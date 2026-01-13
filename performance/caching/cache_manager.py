#!/usr/bin/env python3
"""
Caching Strategies and CDN Integration
Implements multi-layer caching strategies and CDN integration for optimal performance
"""

import asyncio
import time
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps, lru_cache
import pickle
import gzip
import aioredis
import redis
from pathlib import Path
import aiohttp
import aiofiles
import base64

class CacheStrategy(Enum):
    """Cache strategy types"""
    LRU = "lru"
    FIFO = "fifo"
    LFU = "lfu"
    TTL = "ttl"
    ADAPTIVE = "adaptive"

class CacheLevel(Enum):
    """Cache hierarchy levels"""
    L1_MEMORY = "l1_memory"
    L2_REDIS = "l2_redis"
    L3_CDN = "l3_cdn"
    L4_DISK = "l4_disk"

@dataclass
class CacheEntry:
    """Cache entry data structure"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl: Optional[int] = None
    compressed: bool = False
    cache_level: str = "memory"

@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    timestamp: datetime
    cache_level: str
    hits: int
    misses: int
    hit_rate: float
    evictions: int
    total_requests: int
    average_response_time: float
    memory_usage_mb: float
    active_entries: int

@dataclass
class CDNConfiguration:
    """CDN configuration settings"""
    provider: str  # cloudflare, aws_cloudfront, azure_cdn, gcp_cdn
    endpoint: str
    api_key: str
    zone_id: Optional[str] = None
    cache_ttl: int = 3600
    compression_enabled: bool = True
    custom_headers: Dict[str, str] = None

class MemoryCache:
    """High-performance in-memory cache with LRU eviction"""
    
    def __init__(self, max_size_mb: int = 100, max_entries: int = 10000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.logger = logging.getLogger(__name__)
        
        # Cache storage
        self.cache = {}
        self.access_order = []  # For LRU tracking
        self.current_size = 0
        self.metrics = []
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # Check TTL
                if entry.ttl and (time.time() - entry.created_at.timestamp()) > entry.ttl:
                    await self._remove_entry(key)
                    self.misses += 1
                    return None
                
                # Update access statistics
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                self.access_order.remove(key)
                self.access_order.append(key)
                
                self.hits += 1
                return self._deserialize_value(entry.value)
            
            self.misses += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                  compress: bool = False) -> bool:
        """Set value in cache"""
        async with self.lock:
            try:
                serialized_value = self._serialize_value(value)
                
                if compress:
                    serialized_value = gzip.compress(serialized_value)
                
                size_bytes = len(serialized_value)
                
                # Check if we need to evict entries
                while (self.current_size + size_bytes > self.max_size_bytes or 
                       len(self.cache) >= self.max_entries) and self.cache:
                    await self._evict_entry()
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=serialized_value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=1,
                    size_bytes=size_bytes,
                    ttl=ttl,
                    compressed=compress,
                    cache_level=CacheLevel.L1_MEMORY.value
                )
                
                # Store entry
                if key in self.cache:
                    self.current_size -= self.cache[key].size_bytes
                
                self.cache[key] = entry
                self.access_order.append(key)
                self.current_size += size_bytes
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to set cache entry {key}: {e}")
                return False
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        async with self.lock:
            return await self._remove_entry(key)
    
    async def _remove_entry(self, key: str) -> bool:
        """Remove entry from cache"""
        if key in self.cache:
            entry = self.cache[key]
            self.current_size -= entry.size_bytes
            del self.cache[key]
            self.access_order.remove(key)
            return True
        return False
    
    async def _evict_entry(self):
        """Evict entry using LRU strategy"""
        if self.access_order:
            # Remove least recently used entry
            evict_key = self.access_order.pop(0)
            await self._remove_entry(evict_key)
            self.evictions += 1
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            return pickle.dumps(value)
        except Exception:
            # Fallback to JSON serialization
            return json.dumps(value, default=str).encode('utf-8')
    
    def _deserialize_value(self, serialized_value: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            return pickle.loads(serialized_value)
        except Exception:
            # Fallback to JSON deserialization
            return json.loads(serialized_value.decode('utf-8'))
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'evictions': self.evictions,
            'total_requests': total_requests,
            'current_size_mb': self.current_size / (1024 * 1024),
            'max_size_mb': self.max_size_bytes / (1024 * 1024),
            'active_entries': len(self.cache),
            'max_entries': self.max_entries
        }
    
    async def clear(self):
        """Clear all cache entries"""
        async with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.current_size = 0
            self.hits = 0
            self.misses = 0
            self.evictions = 0

class RedisCache:
    """Redis-based distributed cache"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.namespace = config.get('namespace', 'cache')
        
        # Initialize Redis connection
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            redis_config = self.config.get('redis', {})
            
            if redis_config.get('use_async', False):
                # Async Redis for asyncio
                pass  # Would create async Redis instance
            else:
                # Sync Redis client
                self.redis_client = redis.Redis(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    db=redis_config.get('db', 0),
                    password=redis_config.get('password'),
                    decode_responses=False,  # Keep as bytes for serialization
                    socket_timeout=self.config.get('timeout', 5),
                    socket_connect_timeout=self.config.get('connect_timeout', 5),
                    health_check_interval=30
                )
                
                # Test connection
                self.redis_client.ping()
                self.logger.info("Redis cache initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis cache: {e}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            namespaced_key = f"{self.namespace}:{key}"
            cached_value = self.redis_client.get(namespaced_key)
            
            if cached_value:
                return self._deserialize_value(cached_value)
            return None
            
        except Exception as e:
            self.logger.error(f"Redis get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        try:
            namespaced_key = f"{self.namespace}:{key}"
            serialized_value = self._serialize_value(value)
            
            if ttl:
                success = self.redis_client.setex(namespaced_key, ttl, serialized_value)
            else:
                success = self.redis_client.set(namespaced_key, serialized_value)
            
            return bool(success)
            
        except Exception as e:
            self.logger.error(f"Redis set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete entry from Redis cache"""
        try:
            namespaced_key = f"{self.namespace}:{key}"
            result = self.redis_client.delete(namespaced_key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Redis delete failed for key {key}: {e}")
            return False
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        try:
            return pickle.dumps(value)
        except Exception:
            return json.dumps(value, default=str).encode('utf-8')
    
    def _deserialize_value(self, serialized_value: bytes) -> Any:
        """Deserialize value from Redis storage"""
        try:
            return pickle.loads(serialized_value)
        except Exception:
            return json.loads(serialized_value.decode('utf-8'))
    
    async def get_stats(self) -> Dict:
        """Get Redis cache statistics"""
        try:
            info = self.redis_client.info()
            
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_bytes': info.get('used_memory', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'expired_keys': info.get('expired_keys', 0),
                'evicted_keys': info.get('evicted_keys', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get Redis stats: {e}")
            return {}

class CDNCache:
    """CDN-based cache for static content and API responses"""
    
    def __init__(self, config: CDNConfiguration):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = aiohttp.ClientSession()
        
        # Cache mapping for local tracking
        self.local_cache = {}
        self.cache_stats = {'hits': 0, 'misses': 0}
    
    async def get(self, url: str, custom_headers: Dict[str, str] = None) -> Optional[Any]:
        """Get content from CDN cache"""
        try:
            cache_key = f"cdn:{url}"
            
            # Check local cache first
            if cache_key in self.local_cache:
                entry = self.local_cache[cache_key]
                if (datetime.now() - entry['timestamp']).seconds < self.config.cache_ttl:
                    self.cache_stats['hits'] += 1
                    return entry['content']
            
            # Fetch from CDN
            headers = custom_headers or self.config.custom_headers or {}
            headers.update({
                'Cache-Control': f'max-age={self.config.cache_ttl}',
                'Accept-Encoding': 'gzip' if self.config.compression_enabled else 'identity'
            })
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Store in local cache
                    self.local_cache[cache_key] = {
                        'content': content,
                        'timestamp': datetime.now(),
                        'content_type': response.headers.get('Content-Type'),
                        'etag': response.headers.get('ETag')
                    }
                    
                    self.cache_stats['hits'] += 1
                    return content
                else:
                    self.cache_stats['misses'] += 1
                    return None
                    
        except Exception as e:
            self.logger.error(f"CDN get failed for URL {url}: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    async def purge(self, url: str) -> bool:
        """Purge content from CDN cache"""
        try:
            # This would implement actual CDN purge API calls
            # For now, just remove from local cache
            cache_key = f"cdn:{url}"
            if cache_key in self.local_cache:
                del self.local_cache[cache_key]
            
            return True
            
        except Exception as e:
            self.logger.error(f"CDN purge failed for URL {url}: {e}")
            return False
    
    async def set(self, url: str, content: Any, headers: Dict[str, str] = None) -> bool:
        """Set content in CDN cache"""
        try:
            # This would implement actual CDN upload/purge
            # For now, just store locally
            cache_key = f"cdn:{url}"
            self.local_cache[cache_key] = {
                'content': content,
                'timestamp': datetime.now(),
                'headers': headers or {}
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"CDN set failed for URL {url}: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get CDN cache statistics"""
        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'cached_urls': len(self.local_cache),
            'total_requests': self.cache_stats['hits'] + self.cache_stats['misses'],
            'hit_rate': (self.cache_stats['hits'] / 
                        max(1, self.cache_stats['hits'] + self.cache_stats['misses']))
        }

class MultiLevelCache:
    """Multi-level caching system with intelligent routing"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache layers
        self.memory_cache = MemoryCache(
            max_size_mb=config.get('l1_memory', {}).get('max_size_mb', 100),
            max_entries=config.get('l1_memory', {}).get('max_entries', 10000)
        )
        
        if config.get('l2_redis', {}).get('enabled', False):
            self.redis_cache = RedisCache(config['l2_redis'])
        else:
            self.redis_cache = None
        
        if config.get('l3_cdn', {}).get('enabled', False):
            cdn_config = CDNConfiguration(**config['l3_cdn'])
            self.cdn_cache = CDNCache(cdn_config)
        else:
            self.cdn_cache = None
        
        # Cache routing configuration
        self.cache_routing = config.get('cache_routing', {})
        
        # Performance tracking
        self.layer_metrics = {}
    
    async def get(self, key: str, cache_strategy: CacheStrategy = CacheStrategy.LRU) -> Optional[Any]:
        """Get value from multi-level cache"""
        start_time = time.time()
        
        # Try L1 Memory cache first
        value = await self.memory_cache.get(key)
        if value is not None:
            self._record_layer_access(CacheLevel.L1_MEMORY.value, True, time.time() - start_time)
            return value
        
        # Try L2 Redis cache
        if self.redis_cache:
            value = await self.redis_cache.get(key)
            if value is not None:
                self._record_layer_access(CacheLevel.L2_REDIS.value, True, time.time() - start_time)
                # Optionally populate L1 cache
                if self._should_populate_l1(key, cache_strategy):
                    await self.memory_cache.set(key, value)
                return value
        
        # Try L3 CDN cache
        if self.cdn_cache:
            # This would be for CDN-accessible URLs
            cdn_url = self._get_cdn_url(key)
            if cdn_url:
                value = await self.cdn_cache.get(cdn_url)
                if value is not None:
                    self._record_layer_access(CacheLevel.L3_CDN.value, True, time.time() - start_time)
                    return value
        
        self._record_layer_access('all', False, time.time() - start_time)
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                  cache_levels: List[str] = None) -> bool:
        """Set value in multiple cache levels"""
        if cache_levels is None:
            cache_levels = ['l1_memory', 'l2_redis']
        
        results = []
        
        # Set in L1 Memory cache
        if 'l1_memory' in cache_levels:
            result = await self.memory_cache.set(key, value, ttl)
            results.append(result)
        
        # Set in L2 Redis cache
        if 'l2_redis' in cache_levels and self.redis_cache:
            result = await self.redis_cache.set(key, value, ttl)
            results.append(result)
        
        # Set in L3 CDN cache
        if 'l3_cdn' in cache_levels and self.cdn_cache:
            cdn_url = self._get_cdn_url(key)
            if cdn_url:
                result = await self.cdn_cache.set(cdn_url, value)
                results.append(result)
        
        return all(results)
    
    def _should_populate_l1(self, key: str, strategy: CacheStrategy) -> bool:
        """Determine if a value should be populated in L1 cache"""
        # Simple heuristic based on access patterns
        # In production, this would be more sophisticated
        return True
    
    def _get_cdn_url(self, key: str) -> Optional[str]:
        """Convert cache key to CDN URL"""
        # This would implement key to URL mapping
        return None
    
    def _record_layer_access(self, layer: str, hit: bool, response_time: float):
        """Record cache layer access metrics"""
        if layer not in self.layer_metrics:
            self.layer_metrics[layer] = {
                'hits': 0,
                'misses': 0,
                'total_requests': 0,
                'average_response_time': 0,
                'total_response_time': 0
            }
        
        metrics = self.layer_metrics[layer]
        metrics['total_requests'] += 1
        metrics['total_response_time'] += response_time
        
        if hit:
            metrics['hits'] += 1
        else:
            metrics['misses'] += 1
        
        metrics['average_response_time'] = (
            metrics['total_response_time'] / metrics['total_requests']
        )
    
    async def get_cache_stats(self) -> Dict:
        """Get comprehensive cache statistics"""
        stats = {
            'memory_cache': await self.memory_cache.get_stats() if hasattr(self.memory_cache, 'get_stats') else {},
            'layer_metrics': self.layer_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.redis_cache:
            stats['redis_cache'] = await self.redis_cache.get_stats()
        
        if self.cdn_cache:
            stats['cdn_cache'] = self.cdn_cache.get_stats()
        
        return stats
    
    async def clear_cache(self, level: Optional[str] = None):
        """Clear cache at specified level or all levels"""
        if level == 'memory' or level is None:
            await self.memory_cache.clear()
        
        if level == 'redis' or level is None:
            # Redis clear would need implementation
            pass
        
        if level == 'cdn' or level is None:
            # CDN clear would need implementation
            pass

class CacheOptimizer:
    """Cache optimization and analysis tools"""
    
    def __init__(self, multi_cache: MultiLevelCache):
        self.cache = multi_cache
        self.logger = logging.getLogger(__name__)
        
        # Cache analysis data
        self.access_patterns = {}
        self.optimization_recommendations = []
    
    def analyze_cache_efficiency(self) -> Dict:
        """Analyze cache efficiency and generate recommendations"""
        stats = asyncio.run(self.cache.get_cache_stats())
        
        recommendations = []
        
        # Analyze memory cache efficiency
        memory_stats = stats.get('memory_cache', {})
        hit_rate = memory_stats.get('hit_rate', 0)
        
        if hit_rate < 0.8:
            recommendations.append({
                'type': 'memory_cache',
                'priority': 'high',
                'issue': 'Low cache hit rate',
                'recommendation': 'Increase memory cache size or improve caching strategy',
                'current_hit_rate': hit_rate,
                'target_hit_rate': 0.9
            })
        
        # Check cache eviction rates
        evictions = memory_stats.get('evictions', 0)
        if evictions > 100:
            recommendations.append({
                'type': 'memory_cache',
                'priority': 'medium',
                'issue': 'High eviction rate',
                'recommendation': 'Increase cache size or implement better eviction strategy',
                'current_evictions': evictions
            })
        
        return {
            'cache_stats': stats,
            'recommendations': recommendations,
            'overall_efficiency': self._calculate_overall_efficiency(stats)
        }
    
    def _calculate_overall_efficiency(self, stats: Dict) -> float:
        """Calculate overall cache efficiency score"""
        memory_hit_rate = stats.get('memory_cache', {}).get('hit_rate', 0)
        
        # Weighted efficiency calculation
        # 60% memory cache hit rate, 40% other factors
        efficiency = memory_hit_rate * 0.6 + 0.4 * 0.85  # Assume 85% for other layers
        
        return min(1.0, efficiency)
    
    def export_cache_report(self, filepath: str):
        """Export cache performance report"""
        analysis = self.analyze_cache_efficiency()
        
        report = {
            'analysis': analysis,
            'access_patterns': self.access_patterns,
            'recommendations': self.optimization_recommendations,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Cache report exported to {filepath}")

def create_sample_cache_config() -> Dict:
    """Create sample cache configuration"""
    return {
        'l1_memory': {
            'max_size_mb': 100,
            'max_entries': 10000
        },
        'l2_redis': {
            'enabled': True,
            'namespace': 'app_cache',
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'password': None,
                'timeout': 5,
                'connect_timeout': 5
            }
        },
        'l3_cdn': {
            'enabled': False,
            'provider': 'cloudflare',
            'endpoint': 'https://cdn.example.com',
            'api_key': 'your_api_key',
            'cache_ttl': 3600,
            'compression_enabled': True
        },
        'cache_routing': {
            'static_content': ['l1_memory', 'l2_redis', 'l3_cdn'],
            'api_responses': ['l1_memory', 'l2_redis'],
            'database_results': ['l1_memory', 'l2_redis']
        }
    }

def main():
    """Example usage and testing"""
    async def demo_caching():
        # Create sample configuration
        config = create_sample_cache_config()
        
        # Initialize multi-level cache
        multi_cache = MultiLevelCache(config)
        optimizer = CacheOptimizer(multi_cache)
        
        print("Caching Strategies Demo")
        print("=" * 50)
        
        # Test cache operations
        test_data = {
            'users': [
                {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
                {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
            ],
            'settings': {'theme': 'dark', 'language': 'en'},
            'stats': {'visits': 1000, 'conversions': 150}
        }
        
        print("Testing cache operations...")
        
        # Store data in cache
        for key, value in test_data.items():
            await multi_cache.set(key, value, ttl=300)
            print(f"Stored {key} in cache")
        
        # Retrieve data from cache
        for key in test_data.keys():
            value = await multi_cache.get(key)
            if value:
                print(f"Retrieved {key} from cache: {type(value).__name__}")
            else:
                print(f"Cache miss for {key}")
        
        # Get cache statistics
        print("\nCache Statistics:")
        stats = await multi_cache.get_cache_stats()
        for layer, layer_stats in stats.items():
            print(f"  {layer}:")
            if isinstance(layer_stats, dict):
                for stat_key, stat_value in layer_stats.items():
                    print(f"    {stat_key}: {stat_value}")
        
        # Run optimization analysis
        print("\nRunning cache optimization analysis...")
        analysis = optimizer.analyze_cache_efficiency()
        
        print(f"Overall Cache Efficiency: {analysis['overall_efficiency']:.2%}")
        print("\nOptimization Recommendations:")
        for rec in analysis['recommendations']:
            print(f"  {rec['priority'].upper()}: {rec['recommendation']}")
        
        # Export report
        optimizer.export_cache_report('/tmp/cache_analysis_report.json')
        print(f"\nCache analysis report exported")
    
    # Run the demo
    asyncio.run(demo_caching())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()