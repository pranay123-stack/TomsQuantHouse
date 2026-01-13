"""
ObjectStore Caching System for Abacus.AI Predictions
Efficient caching layer to reduce API calls and improve performance
"""

import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

from AlgorithmImports import *


class CacheEntryType(Enum):
    """Cache entry types"""
    PREDICTION = "prediction"
    PRICE_DATA = "price_data"
    FEATURE_DATA = "feature_data"
    METRICS = "metrics"


@dataclass
class CacheEntry:
    """Cache entry data structure"""
    key: str
    data: Any
    timestamp: datetime
    ttl: int  # Time to live in seconds
    entry_type: CacheEntryType
    size_bytes: int
    hit_count: int = 0
    last_access: datetime = None


class AbacusPredictionCache:
    """Prediction caching system using LEAN ObjectStore"""
    
    def __init__(self, algorithm: QCAlgorithm, config: Dict[str, Any] = None):
        """
        Initialize prediction cache
        
        Args:
            algorithm: Reference to LEAN algorithm
            config: Cache configuration
        """
        self.algorithm = algorithm
        self.config = config or {}
        
        # Cache configuration
        self.cache_config = {
            'default_ttl': self.config.get('default_ttl', 3600),  # 1 hour
            'max_cache_size': self.config.get('max_cache_size', 100),  # Max entries
            'auto_cleanup': self.config.get('auto_cleanup', True),
            'cleanup_interval': self.config.get('cleanup_interval', 86400),  # 24 hours
            'enable_compression': self.config.get('enable_compression', False),
            'enable_stats': self.config.get('enable_stats', True)
        }
        
        # Cache storage
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # For LRU eviction
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'errors': 0,
            'total_requests': 0
        }
        
        # ObjectStore prefixes
        self.prefixes = {
            'predictions': 'abacus_predictions',
            'price_data': 'abacus_price_data',
            'feature_data': 'abacus_feature_data',
            'metrics': 'abacus_metrics'
        }
        
        # Thread safety
        self.lock = False
        
        self.Debug("Abacus.AI Prediction Cache initialized")
        self.Debug(f"Cache configuration: {self.cache_config}")
    
    def get(self, key: str, fallback_func: Optional[callable] = None, **kwargs) -> Any:
        """
        Get cached data with fallback
        
        Args:
            key: Cache key
            fallback_func: Function to call if cache miss
            **kwargs: Arguments for fallback function
            
        Returns:
            Cached data or fallback result
        """
        try:
            with self._get_lock():
                self.stats['total_requests'] += 1
                
                # Check cache
                if key in self.cache:
                    entry = self.cache[key]
                    
                    # Check if expired
                    if self._is_expired(entry):
                        self._evict_entry(key)
                        self.Debug(f"Cache entry expired: {key}")
                    else:
                        # Update access statistics
                        self._update_access(key)
                        
                        # Return cached data
                        if self.cache_config['enable_stats']:
                            entry.hit_count += 1
                        self.stats['hits'] += 1
                        
                        self.Debug(f"Cache hit: {key}")
                        return self._deserialize_data(entry.data)
                
                # Cache miss
                self.stats['misses'] += 1
                self.Debug(f"Cache miss: {key}")
                
                # Try ObjectStore fallback
                cached_data = self._get_from_objectstore(key)
                if cached_data is not None:
                    # Re-cache locally
                    self._cache_locally(key, cached_data, entry_type=CacheEntryType.PREDICTION)
                    return self._deserialize_data(cached_data)
                
                # Execute fallback function
                if fallback_func:
                    try:
                        data = fallback_func(**kwargs)
                        if data is not None:
                            # Cache the result
                            self.set(key, data)
                            return data
                    except Exception as e:
                        self.Debug(f"Fallback function failed: {e}")
                        self.stats['errors'] += 1
                
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            self.Debug(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None, entry_type: CacheEntryType = CacheEntryType.PREDICTION) -> bool:
        """
        Set cached data
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds
            entry_type: Type of cache entry
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_lock():
                # Determine TTL
                if ttl is None:
                    ttl = self._get_default_ttl(entry_type)
                
                # Create cache entry
                serialized_data = self._serialize_data(data)
                entry = CacheEntry(
                    key=key,
                    data=serialized_data,
                    timestamp=datetime.now(),
                    ttl=ttl,
                    entry_type=entry_type,
                    size_bytes=len(serialized_data),
                    last_access=datetime.now()
                )
                
                # Cache locally
                self._cache_locally(key, serialized_data, entry_type)
                
                # Store in ObjectStore
                self._store_in_objectstore(key, serialized_data, ttl)
                
                # Check cache size limits
                if len(self.cache) > self.cache_config['max_cache_size']:
                    self._evict_lru_entries()
                
                return True
                
        except Exception as e:
            self.stats['errors'] += 1
            self.Debug(f"Cache set error for key {key}: {e}")
            return False
    
    def _cache_locally(self, key: str, data: Any, entry_type: CacheEntryType, ttl: Optional[int] = None):
        """Cache data locally with LRU management"""
        try:
            if ttl is None:
                ttl = self._get_default_ttl(entry_type)
            
            serialized_data = self._serialize_data(data)
            entry = CacheEntry(
                key=key,
                data=serialized_data,
                timestamp=datetime.now(),
                ttl=ttl,
                entry_type=entry_type,
                size_bytes=len(serialized_data),
                last_access=datetime.now()
            )
            
            # Add to cache
            self.cache[key] = entry
            
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
        except Exception as e:
            self.Debug(f"Local caching error: {e}")
    
    def _store_in_objectstore(self, key: str, data: Any, ttl: int):
        """Store data in LEAN ObjectStore"""
        try:
            if not hasattr(self.algorithm, 'object_store') or self.algorithm.object_store is None:
                return False
            
            # Create full key with type prefix
            type_prefix = self._get_type_prefix(self.cache[key].entry_type if key in self.cache else CacheEntryType.PREDICTION)
            full_key = f"{type_prefix}:{key}"
            
            # Store with JSON serialization
            if self.cache_config['enable_compression']:
                # Compress if enabled (placeholder - actual compression would be implemented)
                cache_data = {
                    'data': data,
                    'timestamp': datetime.now().isoformat(),
                    'ttl': ttl,
                    'compressed': False
                }
            else:
                cache_data = {
                    'data': data,
                    'timestamp': datetime.now().isoformat(),
                    'ttl': ttl,
                    'compressed': False
                }
            
            # Save to ObjectStore
            self.algorithm.object_store.SaveJson(full_key, cache_data)
            
            # Set expiration (ObjectStore handles this automatically)
            return True
            
        except Exception as e:
            self.Debug(f"ObjectStore storage error: {e}")
            return False
    
    def _get_from_objectstore(self, key: str) -> Optional[Any]:
        """Get data from LEAN ObjectStore"""
        try:
            if not hasattr(self.algorithm, 'object_store') or self.algorithm.object_store is None:
                return None
            
            # Try different type prefixes
            for entry_type in CacheEntryType:
                type_prefix = self._get_type_prefix(entry_type)
                full_key = f"{type_prefix}:{key}"
                
                try:
                    cached_data = self.algorithm.object_store.ReadJson(full_key)
                    
                    if cached_data:
                        # Check if data is still valid
                        timestamp = datetime.fromisoformat(cached_data['timestamp'])
                        ttl = cached_data.get('ttl', self.cache_config['default_ttl'])
                        
                        if datetime.now() - timestamp < timedelta(seconds=ttl):
                            return cached_data['data']
                        else:
                            # Remove expired data
                            self._remove_from_objectstore(full_key)
                    
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.Debug(f"ObjectStore retrieval error: {e}")
            return None
    
    def _remove_from_objectstore(self, key: str):
        """Remove data from ObjectStore"""
        try:
            if hasattr(self.algorithm, 'object_store') and self.algorithm.object_store is not None:
                self.algorithm.object_store.Delete(key)
        except Exception as e:
            self.Debug(f"ObjectStore deletion error: {e}")
    
    def _get_type_prefix(self, entry_type: CacheEntryType) -> str:
        """Get type prefix for cache entry"""
        type_map = {
            CacheEntryType.PREDICTION: self.prefixes['predictions'],
            CacheEntryType.PRICE_DATA: self.prefixes['price_data'],
            CacheEntryType.FEATURE_DATA: self.prefixes['feature_data'],
            CacheEntryType.METRICS: self.prefixes['metrics']
        }
        return type_map.get(entry_type, self.prefixes['predictions'])
    
    def _serialize_data(self, data: Any) -> str:
        """Serialize data for storage"""
        try:
            if isinstance(data, str):
                return data
            elif isinstance(data, dict):
                return json.dumps(data)
            else:
                # Use pickle for complex objects
                return pickle.dumps(data).hex()
        except Exception as e:
            self.Debug(f"Data serialization error: {e}")
            return json.dumps(str(data))  # Fallback to string
    
    def _deserialize_data(self, serialized_data: str) -> Any:
        """Deserialize data from storage"""
        try:
            # Try JSON first
            try:
                return json.loads(serialized_data)
            except json.JSONDecodeError:
                # Try pickle if JSON fails
                if len(serialized_data) % 2 == 0:  # Hex string check
                    return pickle.loads(bytes.fromhex(serialized_data))
                else:
                    return serialized_data
        except Exception as e:
            self.Debug(f"Data deserialization error: {e}")
            return serialized_data  # Return as string fallback
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - entry.timestamp > timedelta(seconds=entry.ttl)
    
    def _update_access(self, key: str):
        """Update access statistics"""
        if key in self.cache:
            self.cache[key].last_access = datetime.now()
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
    
    def _evict_entry(self, key: str):
        """Evict a single cache entry"""
        try:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                self.stats['evictions'] += 1
        except Exception as e:
            self.Debug(f"Entry eviction error: {e}")
    
    def _evict_lru_entries(self):
        """Evict least recently used entries"""
        try:
            while len(self.cache) > self.cache_config['max_cache_size']:
                if not self.access_order:
                    break
                
                # Remove oldest accessed entry
                oldest_key = self.access_order.pop(0)
                if oldest_key in self.cache:
                    del self.cache[oldest_key]
                    self.stats['evictions'] += 1
                
        except Exception as e:
            self.Debug(f"LRU eviction error: {e}")
    
    def _get_default_ttl(self, entry_type: CacheEntryType) -> int:
        """Get default TTL for entry type"""
        ttl_map = {
            CacheEntryType.PREDICTION: 3600,  # 1 hour
            CacheEntryType.PRICE_DATA: 900,   # 15 minutes
            CacheEntryType.FEATURE_DATA: 7200, # 2 hours
            CacheEntryType.METRICS: 1800      # 30 minutes
        }
        return ttl_map.get(entry_type, self.cache_config['default_ttl'])
    
    def _get_lock(self):
        """Get threading lock (simplified for LEAN environment)"""
        return self.lock if hasattr(self, 'lock') else None
    
    def clear_cache(self, entry_type: Optional[CacheEntryType] = None) -> int:
        """
        Clear cache entries
        
        Args:
            entry_type: Specific entry type to clear, or None for all
            
        Returns:
            Number of entries cleared
        """
        try:
            with self._get_lock():
                keys_to_remove = []
                
                for key, entry in self.cache.items():
                    if entry_type is None or entry.entry_type == entry_type:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    self._evict_entry(key)
                
                # Clear from ObjectStore as well
                if entry_type is None:
                    # Clear all types
                    for prefix in self.prefixes.values():
                        self._clear_objectstore_by_prefix(prefix)
                else:
                    # Clear specific type
                    prefix = self._get_type_prefix(entry_type)
                    self._clear_objectstore_by_prefix(prefix)
                
                cleared_count = len(keys_to_remove)
                self.Debug(f"Cleared {cleared_count} cache entries")
                return cleared_count
                
        except Exception as e:
            self.stats['errors'] += 1
            self.Debug(f"Cache clear error: {e}")
            return 0
    
    def _clear_objectstore_by_prefix(self, prefix: str):
        """Clear ObjectStore entries by prefix (simplified)"""
        try:
            if not hasattr(self.algorithm, 'object_store') or self.algorithm.object_store is None:
                return
            
            # This is a simplified implementation
            # In a real implementation, you'd iterate through all keys
            # and delete those matching the prefix
            pass
            
        except Exception as e:
            self.Debug(f"ObjectStore prefix clear error: {e}")
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        try:
            with self._get_lock():
                expired_keys = []
                
                for key, entry in self.cache.items():
                    if self._is_expired(entry):
                        expired_keys.append(key)
                
                for key in expired_keys:
                    self._evict_entry(key)
                
                self.Debug(f"Cleaned up {len(expired_keys)} expired entries")
                return len(expired_keys)
                
        except Exception as e:
            self.stats['errors'] += 1
            self.Debug(f"Expired cleanup error: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            total_requests = self.stats['total_requests']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                'cache_size': len(self.cache),
                'total_requests': total_requests,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self.stats['evictions'],
                'errors': self.stats['errors'],
                'memory_usage_bytes': sum(entry.size_bytes for entry in self.cache.values()),
                'cache_config': self.cache_config,
                'last_update': datetime.now()
            }
            
        except Exception as e:
            self.Debug(f"Stats retrieval error: {e}")
            return {'error': str(e)}
    
    def generate_cache_key(self, symbol: str, date: datetime, prediction_type: str = '1d') -> str:
        """
        Generate standardized cache key
        
        Args:
            symbol: Symbol to generate key for
            date: Date for prediction
            prediction_type: Type of prediction (1d, 5d, 30d)
            
        Returns:
            Generated cache key
        """
        # Create consistent key format
        key_parts = [
            symbol,
            date.strftime('%Y%m%d_%H%M'),
            prediction_type,
            'v1'  # Version
        ]
        
        key_string = '_'.join(key_parts)
        
        # Create hash for consistent length
        hash_object = hashlib.md5(key_string.encode())
        return f"pred_{hash_object.hexdigest()[:16]}"
    
    def preload_predictions(self, symbols: List[str], date: datetime) -> Dict[str, bool]:
        """
        Preload predictions for multiple symbols
        
        Args:
            symbols: List of symbols to preload
            date: Date for predictions
            
        Returns:
            Dictionary of symbol -> success status
        """
        results = {}
        
        for symbol in symbols:
            try:
                key = self.generate_cache_key(symbol, date)
                
                # Check if already cached
                if key not in self.cache:
                    # This would trigger the actual data loading
                    # For now, just mark as success
                    results[symbol] = True
                else:
                    results[symbol] = False  # Already cached
                
            except Exception as e:
                self.Debug(f"Preload failed for {symbol}: {e}")
                results[symbol] = False
        
        return results
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache performance"""
        try:
            with self._get_lock():
                results = {
                    'cleaned_expired': 0,
                    'evicted_entries': 0,
                    'reduced_memory': 0
                }
                
                initial_memory = sum(entry.size_bytes for entry in self.cache.values())
                
                # Clean expired entries
                results['cleaned_expired'] = self.cleanup_expired()
                
                # Optimize cache size if needed
                if len(self.cache) > self.cache_config['max_cache_size']:
                    initial_size = len(self.cache)
                    self._evict_lru_entries()
                    results['evicted_entries'] = initial_size - len(self.cache)
                
                # Recalculate memory usage
                final_memory = sum(entry.size_bytes for entry in self.cache.values())
                results['reduced_memory'] = initial_memory - final_memory
                
                self.Debug(f"Cache optimization completed: {results}")
                return results
                
        except Exception as e:
            self.Debug(f"Cache optimization error: {e}")
            return {'error': str(e)}


# Global cache instance
_global_cache = None

def get_prediction_cache(algorithm: QCAlgorithm, config: Dict[str, Any] = None) -> AbacusPredictionCache:
    """Get or create global prediction cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = AbacusPredictionCache(algorithm, config)
    return _global_cache