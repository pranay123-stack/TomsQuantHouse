"""
Rate limiting system for Composio MCP Server.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting."""
    
    def __init__(self, settings):
        """Initialize rate limiter."""
        self.settings = settings
        self.redis_client = None
        
        # Rate limit configurations
        self.default_limits = settings.rate_limit.default_limits
        self.tool_specific_limits = settings.rate_limit.tool_specific_limits
        
        # In-memory fallback rate limiting
        self.local_rates = {}
        
        self._setup_redis()
        logger.info("Rate limiter initialized")
    
    def _setup_redis(self):
        """Setup Redis client for rate limiting."""
        try:
            redis_url = self.settings.rate_limit.redis_url.replace("redis://", "redis://")
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis rate limiter initialized")
        except Exception as e:
            logger.warning("Failed to initialize Redis for rate limiting", error=str(e))
            self.redis_client = None
    
    def _get_limit_key(self, user_id: str, tool_name: str, limit_type: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"rate_limit:{user_id}:{tool_name}:{limit_type}"
    
    def _get_local_key(self, user_id: str, tool_name: str) -> str:
        """Generate local storage key."""
        return f"{user_id}:{tool_name}"
    
    async def check_rate_limit(self, user_id: str, tool_name: str) -> bool:
        """Check if user is within rate limits for tool."""
        if not self.settings.rate_limit.enabled:
            return True
        
        try:
            # Get tool-specific limits or use defaults
            tool_limits = self.tool_specific_limits.get(tool_name, self.default_limits)
            
            for limit_type, max_requests in tool_limits.items():
                if not await self._check_single_limit(user_id, tool_name, limit_type, max_requests):
                    logger.warning(
                        "Rate limit exceeded",
                        user_id=user_id,
                        tool=tool_name,
                        limit_type=limit_type,
                        max_requests=max_requests
                    )
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Rate limit check failed", user_id=user_id, tool=tool_name, error=str(e))
            # In case of error, allow the request but log the issue
            return True
    
    async def _check_single_limit(
        self, 
        user_id: str, 
        tool_name: str, 
        limit_type: str, 
        max_requests: int
    ) -> bool:
        """Check a single rate limit."""
        current_time = time.time()
        
        if self.redis_client:
            return await self._check_redis_limit(user_id, tool_name, limit_type, max_requests, current_time)
        else:
            return await self._check_local_limit(user_id, tool_name, limit_type, max_requests, current_time)
    
    async def _check_redis_limit(
        self, 
        user_id: str, 
        tool_name: str, 
        limit_type: str, 
        max_requests: int, 
        current_time: float
    ) -> bool:
        """Check rate limit using Redis."""
        key = self._get_limit_key(user_id, tool_name, limit_type)
        
        if limit_type == "requests_per_minute":
            window = 60
        elif limit_type == "requests_per_hour":
            window = 3600
        elif limit_type == "requests_per_day":
            window = 86400
        else:
            window = 60  # Default to 1 minute
        
        try:
            pipe = self.redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, current_time - window)
            
            # Count current requests
            pipe.zcard(key)
            
            # If under limit, add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry
            pipe.expire(key, window)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            return current_requests < max_requests
            
        except Exception as e:
            logger.error("Redis rate limit check failed", error=str(e))
            return True  # Allow request if Redis fails
    
    async def _check_local_limit(
        self, 
        user_id: str, 
        tool_name: str, 
        limit_type: str, 
        max_requests: int, 
        current_time: float
    ) -> bool:
        """Check rate limit using local memory (fallback)."""
        key = self._get_local_key(user_id, tool_name)
        
        if key not in self.local_rates:
            self.local_rates[key] = {
                "requests_per_minute": [],
                "requests_per_hour": [],
                "requests_per_day": []
            }
        
        # Clean old requests based on window size
        windows = {
            "requests_per_minute": 60,
            "requests_per_hour": 3600,
            "requests_per_day": 86400
        }
        
        window = windows.get(limit_type, 60)
        cutoff_time = current_time - window
        
        # Remove old requests
        self.local_rates[key][limit_type] = [
            req_time for req_time in self.local_rates[key][limit_type]
            if req_time > cutoff_time
        ]
        
        # Check if under limit
        current_requests = len(self.local_rates[key][limit_type])
        
        if current_requests < max_requests:
            # Add current request
            self.local_rates[key][limit_type].append(current_time)
            return True
        
        return False
    
    async def record_request(self, user_id: str, tool_name: str):
        """Record a request for rate limiting."""
        if not self.settings.rate_limit.enabled:
            return
        
        current_time = time.time()
        
        if self.redis_client:
            await self._record_redis_request(user_id, tool_name, current_time)
        else:
            await self._record_local_request(user_id, tool_name, current_time)
    
    async def _record_redis_request(self, user_id: str, tool_name: str, current_time: float):
        """Record request in Redis."""
        try:
            # Get tool-specific limits
            tool_limits = self.tool_specific_limits.get(tool_name, self.default_limits)
            
            pipe = self.redis_client.pipeline()
            
            for limit_type in tool_limits.keys():
                key = self._get_limit_key(user_id, tool_name, limit_type)
                
                # Determine window size
                if limit_type == "requests_per_minute":
                    window = 60
                elif limit_type == "requests_per_hour":
                    window = 3600
                elif limit_type == "requests_per_day":
                    window = 86400
                else:
                    window = 60
                
                # Remove old entries and add current one
                pipe.zremrangebyscore(key, 0, current_time - window)
                pipe.zadd(key, {str(current_time): current_time})
                pipe.expire(key, window)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error("Failed to record Redis request", error=str(e))
    
    async def _record_local_request(self, user_id: str, tool_name: str, current_time: float):
        """Record request in local memory."""
        try:
            key = self._get_local_key(user_id, tool_name)
            
            if key not in self.local_rates:
                self.local_rates[key] = {
                    "requests_per_minute": [],
                    "requests_per_hour": [],
                    "requests_per_day": []
                }
            
            # Add current time to all rate limit windows
            for limit_type in ["requests_per_minute", "requests_per_hour", "requests_per_day"]:
                self.local_rates[key][limit_type].append(current_time)
            
            # Cleanup old entries periodically
            await self._cleanup_local_rates()
            
        except Exception as e:
            logger.error("Failed to record local request", error=str(e))
    
    async def _cleanup_local_rates(self):
        """Clean up old entries from local rate limiting."""
        current_time = time.time()
        cutoff_time = current_time - 86400  # Keep at most 1 day
        
        for key in list(self.local_rates.keys()):
            for limit_type in ["requests_per_minute", "requests_per_hour", "requests_per_day"]:
                self.local_rates[key][limit_type] = [
                    req_time for req_time in self.local_rates[key][limit_type]
                    if req_time > cutoff_time
                ]
            
            # Remove empty entries
            if all(len(self.local_rates[key][lt]) == 0 for lt in ["requests_per_minute", "requests_per_hour", "requests_per_day"]):
                del self.local_rates[key]
    
    async def get_status(self, user_id: str, tool_name: str) -> Dict[str, Any]:
        """Get current rate limit status for user and tool."""
        if not self.settings.rate_limit.enabled:
            return {"enabled": False}
        
        try:
            # Get tool-specific limits or use defaults
            tool_limits = self.tool_specific_limits.get(tool_name, self.default_limits)
            
            status = {
                "enabled": True,
                "user_id": user_id,
                "tool": tool_name,
                "limits": {}
            }
            
            current_time = time.time()
            
            for limit_type, max_requests in tool_limits.items():
                current_count = await self._get_current_count(user_id, tool_name, limit_type, current_time)
                reset_time = self._get_reset_time(limit_type, current_time)
                
                status["limits"][limit_type] = {
                    "max_requests": max_requests,
                    "current_count": current_count,
                    "remaining": max(0, max_requests - current_count),
                    "reset_time": reset_time,
                    "reset_timestamp": int(reset_time.timestamp())
                }
            
            return status
            
        except Exception as e:
            logger.error("Failed to get rate limit status", user_id=user_id, tool=tool_name, error=str(e))
            return {"enabled": False, "error": str(e)}
    
    async def _get_current_count(self, user_id: str, tool_name: str, limit_type: str, current_time: float) -> int:
        """Get current request count for a specific limit."""
        if self.redis_client:
            return await self._get_redis_count(user_id, tool_name, limit_type, current_time)
        else:
            return await self._get_local_count(user_id, tool_name, limit_type, current_time)
    
    async def _get_redis_count(self, user_id: str, tool_name: str, limit_type: str, current_time: float) -> int:
        """Get current count from Redis."""
        try:
            key = self._get_limit_key(user_id, tool_name, limit_type)
            
            if limit_type == "requests_per_minute":
                window = 60
            elif limit_type == "requests_per_hour":
                window = 3600
            elif limit_type == "requests_per_day":
                window = 86400
            else:
                window = 60
            
            cutoff_time = current_time - window
            return await self.redis_client.zcount(key, cutoff_time, current_time)
            
        except Exception as e:
            logger.error("Failed to get Redis count", error=str(e))
            return 0
    
    async def _get_local_count(self, user_id: str, tool_name: str, limit_type: str, current_time: float) -> int:
        """Get current count from local storage."""
        try:
            key = self._get_local_key(user_id, tool_name)
            
            if key not in self.local_rates:
                return 0
            
            # Determine window size
            windows = {
                "requests_per_minute": 60,
                "requests_per_hour": 3600,
                "requests_per_day": 86400
            }
            
            window = windows.get(limit_type, 60)
            cutoff_time = current_time - window
            
            # Count requests within window
            return len([
                req_time for req_time in self.local_rates[key][limit_type]
                if req_time > cutoff_time
            ])
            
        except Exception as e:
            logger.error("Failed to get local count", error=str(e))
            return 0
    
    def _get_reset_time(self, limit_type: str, current_time: float) -> datetime:
        """Get reset time for a limit type."""
        if limit_type == "requests_per_minute":
            return datetime.fromtimestamp(int(current_time / 60) * 60 + 60)
        elif limit_type == "requests_per_hour":
            return datetime.fromtimestamp(int(current_time / 3600) * 3600 + 3600)
        elif limit_type == "requests_per_day":
            reset_datetime = datetime.fromtimestamp(current_time)
            reset_datetime = reset_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            return reset_datetime + timedelta(days=1)
        else:
            return datetime.fromtimestamp(current_time + 60)
    
    async def reset_user_limits(self, user_id: str, tool_name: Optional[str] = None):
        """Reset rate limits for a user (admin function)."""
        try:
            if tool_name:
                tools = [tool_name]
            else:
                tools = list(self.tool_specific_limits.keys()) + ["default"]
            
            if self.redis_client:
                await self._reset_redis_limits(user_id, tools)
            else:
                await self._reset_local_limits(user_id, tools)
            
            logger.info("Rate limits reset", user_id=user_id, tool=tool_name)
            
        except Exception as e:
            logger.error("Failed to reset rate limits", user_id=user_id, tool=tool_name, error=str(e))
    
    async def _reset_redis_limits(self, user_id: str, tools: List[str]):
        """Reset Redis rate limits."""
        try:
            pipe = self.redis_client.pipeline()
            
            for tool_name in tools:
                tool_limits = self.tool_specific_limits.get(tool_name, self.default_limits)
                
                for limit_type in tool_limits.keys():
                    key = self._get_limit_key(user_id, tool_name, limit_type)
                    pipe.delete(key)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error("Failed to reset Redis limits", error=str(e))
    
    async def _reset_local_limits(self, user_id: str, tools: List[str]):
        """Reset local rate limits."""
        try:
            for tool_name in tools:
                key = self._get_local_key(user_id, tool_name)
                if key in self.local_rates:
                    del self.local_rates[key]
                    
        except Exception as e:
            logger.error("Failed to reset local limits", error=str(e))
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics."""
        try:
            stats = {
                "enabled": self.settings.rate_limit.enabled,
                "redis_available": self.redis_client is not None,
                "tool_limits": list(self.tool_specific_limits.keys()),
                "default_limits": self.default_limits
            }
            
            if not self.redis_client:
                stats["local_rate_count"] = len(self.local_rates)
                
                # Count requests by tool
                tool_counts = {}
                for key, data in self.local_rates.items():
                    tool = key.split(":")[1] if ":" in key else "unknown"
                    total_requests = sum(len(data[lt]) for lt in data.values())
                    tool_counts[tool] = tool_counts.get(tool, 0) + total_requests
                
                stats["tool_request_counts"] = tool_counts
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get global stats", error=str(e))
            return {"error": str(e)}
    
    async def close(self):
        """Close rate limiter connections."""
        if self.redis_client:
            await self.redis_client.close()