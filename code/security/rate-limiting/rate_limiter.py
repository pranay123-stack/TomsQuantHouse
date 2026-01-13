"""
Redis-based Rate Limiting System
Implements various rate limiting algorithms with Redis storage
"""

import redis
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import hashlib
import threading
from collections import defaultdict


class RateLimitAlgorithm(Enum):
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitStrategy:
    """Base rate limiting strategy"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.prefix = "rate_limit:"
    
    def _get_key(self, identifier: str, window: str = None) -> str:
        """Generate Redis key for rate limiting"""
        if window:
            return f"{self.prefix}{identifier}:{window}"
        return f"{self.prefix}{identifier}"
    
    def _get_time_window(self, window_size: int) -> str:
        """Get time window identifier"""
        return int(time.time() // window_size)


class SlidingWindowRateLimiter(RateLimitStrategy):
    """Sliding Window Rate Limiter"""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        self.algorithm = RateLimitAlgorithm.SLIDING_WINDOW
    
    def check_rate_limit(self, identifier: str, limit: int, 
                        window_seconds: int) -> Dict[str, Any]:
        """Check rate limit using sliding window algorithm"""
        current_time = time.time()
        window_size = window_seconds
        
        # Key for this request
        key = self._get_key(identifier)
        
        # Get current window start
        current_window = int(current_time // window_size)
        
        # Remove old entries (older than window)
        cutoff_time = current_time - window_size
        self.redis.zremrangebyscore(key, 0, cutoff_time)
        
        # Count requests in current window
        current_requests = self.redis.zcard(key)
        
        if current_requests >= limit:
            # Rate limit exceeded
            return {
                'allowed': False,
                'current_count': current_requests,
                'limit': limit,
                'reset_time': int((current_window + 1) * window_size),
                'retry_after': int((current_window + 1) * window_size - current_time)
            }
        
        # Add current request
        timestamp = current_time * 1000000  # Microsecond precision
        self.redis.zadd(key, {str(timestamp): timestamp})
        self.redis.expire(key, window_size)
        
        return {
            'allowed': True,
            'current_count': current_requests + 1,
            'limit': limit,
            'remaining': limit - current_requests - 1,
            'reset_time': int((current_window + 1) * window_size)
        }


class FixedWindowRateLimiter(RateLimitStrategy):
    """Fixed Window Rate Limiter"""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        self.algorithm = RateLimitAlgorithm.FIXED_WINDOW
    
    def check_rate_limit(self, identifier: str, limit: int,
                        window_seconds: int) -> Dict[str, Any]:
        """Check rate limit using fixed window algorithm"""
        current_time = time.time()
        window = self._get_time_window(window_seconds)
        
        # Key for this window
        key = self._get_key(identifier, str(window))
        
        # Get current count
        count = int(self.redis.get(key) or 0)
        
        if count >= limit:
            # Rate limit exceeded
            reset_time = int((window + 1) * window_seconds)
            return {
                'allowed': False,
                'current_count': count,
                'limit': limit,
                'reset_time': reset_time,
                'retry_after': reset_time - int(current_time)
            }
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, window_seconds * 2)  # Keep for 2 windows
        pipe.execute()
        
        remaining = limit - count - 1
        reset_time = int((window + 1) * window_seconds)
        
        return {
            'allowed': True,
            'current_count': count + 1,
            'limit': limit,
            'remaining': remaining,
            'reset_time': reset_time
        }


class TokenBucketRateLimiter(RateLimitStrategy):
    """Token Bucket Rate Limiter"""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        self.algorithm = RateLimitAlgorithm.TOKEN_BUCKET
    
    def check_rate_limit(self, identifier: str, capacity: int,
                        refill_rate: float, window_seconds: int) -> Dict[str, Any]:
        """Check rate limit using token bucket algorithm"""
        current_time = time.time()
        key = self._get_key(identifier)
        
        # Get current bucket state
        bucket_data = self.redis.hgetall(key)
        
        if not bucket_data:
            # Initialize new bucket
            bucket_data = {
                'tokens': str(capacity),
                'last_refill': str(current_time)
            }
        else:
            bucket_data = {
                k.decode(): v.decode() 
                for k, v in bucket_data.items()
            }
        
        # Calculate tokens to add based on time passed
        last_refill = float(bucket_data['last_refill'])
        tokens = float(bucket_data['tokens'])
        
        time_passed = current_time - last_refill
        tokens_to_add = time_passed * refill_rate
        
        tokens = min(capacity, tokens + tokens_to_add)
        
        if tokens < 1:
            # No tokens available
            reset_time = int(current_time + (1 - tokens) / refill_rate)
            return {
                'allowed': False,
                'current_tokens': int(tokens),
                'capacity': capacity,
                'refill_rate': refill_rate,
                'reset_time': reset_time,
                'retry_after': int(reset_time - current_time)
            }
        
        # Consume one token
        tokens -= 1
        
        # Update bucket
        pipe = self.redis.pipeline()
        pipe.hset(key, 'tokens', tokens)
        pipe.hset(key, 'last_refill', current_time)
        pipe.expire(key, window_seconds)
        pipe.execute()
        
        return {
            'allowed': True,
            'current_tokens': int(tokens),
            'capacity': capacity,
            'refill_rate': refill_rate,
            'remaining': int(tokens)
        }


class LeakyBucketRateLimiter(RateLimitStrategy):
    """Leaky Bucket Rate Limiter"""
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        self.algorithm = RateLimitAlgorithm.LEAKY_BUCKET
    
    def check_rate_limit(self, identifier: str, capacity: int,
                        leak_rate: float) -> Dict[str, Any]:
        """Check rate limit using leaky bucket algorithm"""
        current_time = time.time()
        key = self._get_key(identifier)
        
        # Get current queue size
        queue_size = int(self.redis.get(key) or 0)
        
        if queue_size >= capacity:
            # Bucket is full
            return {
                'allowed': False,
                'current_queue': queue_size,
                'capacity': capacity,
                'leak_rate': leak_rate,
                'retry_after': int(1 / leak_rate)
            }
        
        # Add request to queue
        pipe = self.redis.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, int(capacity / leak_rate) + 60)  # Keep bucket alive
        pipe.execute()
        
        return {
            'allowed': True,
            'current_queue': queue_size + 1,
            'capacity': capacity,
            'leak_rate': leak_rate,
            'remaining': capacity - queue_size - 1
        }


class RateLimitManager:
    """Main Rate Limiting Manager"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, 
                 redis_db: int = 0, redis_password: str = None):
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        
        # Initialize limiters
        self.sliding_window = SlidingWindowRateLimiter(self.redis_client)
        self.fixed_window = FixedWindowRateLimiter(self.redis_client)
        self.token_bucket = TokenBucketRateLimiter(self.redis_client)
        self.leaky_bucket = LeakyBucketRateLimiter(self.redis_client)
        
        # Rate limit configurations
        self.default_configs = {
            'api_requests': {
                'algorithm': RateLimitAlgorithm.SLIDING_WINDOW,
                'limit': 100,
                'window': 60  # 100 requests per minute
            },
            'login_attempts': {
                'algorithm': RateLimitAlgorithm.SLIDING_WINDOW,
                'limit': 5,
                'window': 300  # 5 attempts per 5 minutes
            },
            'api_key_requests': {
                'algorithm': RateLimitAlgorithm.TOKEN_BUCKET,
                'capacity': 50,
                'refill_rate': 0.8,  # 0.8 tokens per second
                'window': 3600
            }
        }
        
        # Cleanup job
        self._start_cleanup_job()
    
    def check_rate_limit(self, identifier: str, limit_type: str = 'api_requests',
                        custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check rate limit for identifier"""
        # Get configuration
        if custom_config:
            config = custom_config
        else:
            config = self.default_configs.get(limit_type, self.default_configs['api_requests'])
        
        algorithm = config['algorithm']
        identifier_key = f"{limit_type}:{identifier}"
        
        # Route to appropriate limiter
        if algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return self.sliding_window.check_rate_limit(
                identifier_key, config['limit'], config['window']
            )
        elif algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return self.fixed_window.check_rate_limit(
                identifier_key, config['limit'], config['window']
            )
        elif algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return self.token_bucket.check_rate_limit(
                identifier_key, config['capacity'], 
                config['refill_rate'], config['window']
            )
        elif algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            return self.leaky_bucket.check_rate_limit(
                identifier_key, config['capacity'], config['leak_rate']
            )
        else:
            raise ValueError(f"Unknown rate limit algorithm: {algorithm}")
    
    def get_rate_limit_stats(self, identifier: str = None) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        if identifier:
            # Get stats for specific identifier
            pattern = f"*:{identifier}"
            keys = self.redis_client.keys(pattern)
            
            stats = {}
            for key in keys:
                key_type, actual_id = key.split(':', 1)[-2:]
                rate_limit_data = self.redis_client.get(key)
                if rate_limit_data:
                    stats[actual_id] = {
                        'key_type': key_type,
                        'count': int(rate_limit_data),
                        'last_accessed': datetime.fromtimestamp(
                            self.redis_client.ttl(key) or 0
                        ).isoformat()
                    }
            return stats
        else:
            # Get overall stats
            pattern = f"{self.sliding_window.prefix}*"
            keys = self.redis_client.keys(pattern)
            
            return {
                'total_keys': len(keys),
                'algorithms_used': [alg.value for alg in RateLimitAlgorithm],
                'default_configs': self.default_configs
            }
    
    def configure_rate_limit(self, name: str, config: Dict[str, Any]):
        """Configure custom rate limit"""
        self.default_configs[name] = config
    
    def block_identifier(self, identifier: str, duration_seconds: int):
        """Block identifier for specified duration"""
        key = f"blocked:{identifier}"
        self.redis_client.setex(key, duration_seconds, "1")
    
    def unblock_identifier(self, identifier: str):
        """Unblock identifier"""
        key = f"blocked:{identifier}"
        self.redis_client.delete(key)
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked"""
        key = f"blocked:{identifier}"
        return bool(self.redis_client.exists(key))
    
    def get_blocked_identifiers(self) -> List[str]:
        """Get list of blocked identifiers"""
        pattern = "blocked:*"
        keys = self.redis_client.keys(pattern)
        return [key.split(':', 1)[1] for key in keys]
    
    def cleanup_expired_keys(self) -> int:
        """Clean up expired rate limit keys"""
        pattern = f"{self.sliding_window.prefix}*"
        keys = self.redis_client.keys(pattern)
        
        cleaned = 0
        for key in keys:
            if self.redis_client.ttl(key) <= 0:
                self.redis_client.delete(key)
                cleaned += 1
        
        return cleaned
    
    def _start_cleanup_job(self):
        """Start background cleanup job"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Run every 5 minutes
                    self.cleanup_expired_keys()
                except Exception as e:
                    print(f"Cleanup job error: {e}")
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    def get_redis_info(self) -> Dict[str, Any]:
        """Get Redis connection info"""
        try:
            info = self.redis_client.info()
            return {
                'connected': True,
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed')
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }


class RateLimitMiddleware:
    """Middleware for rate limiting"""
    
    def __init__(self, rate_limiter: RateLimitManager):
        self.rate_limiter = rate_limiter
    
    def check_request_limit(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check rate limit for request"""
        identifier = self._get_identifier(request_data)
        limit_type = request_data.get('limit_type', 'api_requests')
        
        # Check if blocked
        if self.rate_limiter.is_blocked(identifier):
            return {
                'allowed': False,
                'error': 'Request blocked',
                'status': 429,
                'retry_after': 3600
            }
        
        # Check rate limit
        result = self.rate_limiter.check_rate_limit(identifier, limit_type)
        
        return {
            'allowed': result['allowed'],
            'rate_limit_info': result,
            'identifier': identifier
        }
    
    def _get_identifier(self, request_data: Dict[str, Any]) -> str:
        """Extract identifier from request"""
        # Priority: API key > IP address > User ID
        if 'api_key' in request_data:
            return f"api_key:{hashlib.md5(request_data['api_key'].encode()).hexdigest()}"
        elif 'ip_address' in request_data:
            return f"ip:{request_data['ip_address']}"
        elif 'user_id' in request_data:
            return f"user:{request_data['user_id']}"
        else:
            return f"unknown:{request_data.get('request_id', 'default')}"


# Example usage and testing
if __name__ == "__main__":
    # Initialize rate limiter (requires Redis)
    try:
        rate_limiter = RateLimitManager(redis_host="localhost")
        
        # Test sliding window
        print("Testing Sliding Window Rate Limiter:")
        for i in range(5):
            result = rate_limiter.check_rate_limit("test_user", "api_requests")
            print(f"Request {i+1}: {'Allowed' if result['allowed'] else 'Blocked'}")
        
        # Test token bucket
        print("\nTesting Token Bucket Rate Limiter:")
        for i in range(10):
            result = rate_limiter.check_rate_limit("api_client", "api_key_requests")
            print(f"Request {i+1}: {'Allowed' if result['allowed'] else 'Blocked'}, "
                  f"Tokens: {result.get('current_tokens', 0)}")
        
        # Get stats
        stats = rate_limiter.get_rate_limit_stats()
        print(f"\nRate Limit Stats: {stats}")
        
    except Exception as e:
        print(f"Redis connection failed: {e}")
        print("Run with Redis server or mock the connection for testing")
