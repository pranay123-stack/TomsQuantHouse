"""
ASYMEdge Dashboard API - Rate Limiting Middleware

Rate limiting middleware providing:
- Request rate limiting per user/IP
- Endpoint-specific rate limits
- Burst limiting and sliding windows
- Custom rate limit responses
- Rate limit persistence and monitoring
"""

import time
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging
import hashlib

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import settings

logger = logging.getLogger(__name__)

class RateLimitStore:
    """In-memory rate limit storage (use Redis in production)"""
    
    def __init__(self):
        # Structure: {key: {"requests": deque([timestamps]), "reset_time": timestamp}}
        self._limits: Dict[str, Dict[str, Any]] = {}
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._last_cleanup = time.time()
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate rate limit key"""
        return f"{identifier}:{endpoint}"
    
    def check_rate_limit(self, identifier: str, endpoint: str, 
                        max_requests: int, window_seconds: int) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limit"""
        current_time = time.time()
        key = self._get_key(identifier, endpoint)
        
        if key not in self._limits:
            self._limits[key] = {
                "requests": deque(),
                "reset_time": current_time + window_seconds
            }
        
        rate_data = self._limits[key]
        request_times = rate_data["requests"]
        
        # Clean old requests outside the window
        cutoff_time = current_time - window_seconds
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
        
        # Check if limit exceeded
        if len(request_times) >= max_requests:
            reset_time = rate_data["reset_time"]
            retry_after = int(reset_time - current_time)
            
            return False, {
                "limit": max_requests,
                "remaining": 0,
                "reset_time": reset_time,
                "retry_after": retry_after,
                "window": window_seconds
            }
        
        # Add current request
        request_times.append(current_time)
        
        # Update reset time if needed
        if rate_data["reset_time"] < current_time:
            rate_data["reset_time"] = current_time + window_seconds
        
        return True, {
            "limit": max_requests,
            "remaining": max_requests - len(request_times),
            "reset_time": rate_data["reset_time"],
            "retry_after": 0,
            "window": window_seconds
        }
    
    def cleanup_old_entries(self):
        """Clean up old rate limit entries"""
        current_time = time.time()
        
        # Remove entries that have expired
        expired_keys = []
        for key, rate_data in self._limits.items():
            if rate_data["reset_time"] < current_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._limits[key]
        
        self._last_cleanup = current_time

# Global rate limit store
rate_limit_store = RateLimitStore()

class RateLimitConfig:
    """Rate limit configuration"""
    
    # Default rate limits by endpoint type
    ENDPOINT_LIMITS = {
        # Authentication endpoints
        "auth": {"requests": 5, "window": 300},  # 5 requests per 5 minutes
        
        # Agent endpoints
        "agents_create": {"requests": 10, "window": 3600},  # 10 per hour
        "agents_query": {"requests": 100, "window": 3600},  # 100 per hour
        "agents_status": {"requests": 60, "window": 3600},  # 60 per hour
        
        # Trading endpoints
        "trading_metrics": {"requests": 1000, "window": 3600},  # 1000 per hour
        "trading_data": {"requests": 500, "window": 3600},  # 500 per hour
        
        # Workflow endpoints
        "workflows_create": {"requests": 20, "window": 3600},  # 20 per hour
        "workflows_status": {"requests": 100, "window": 3600},  # 100 per hour
        
        # Dashboard endpoints
        "dashboard_config": {"requests": 50, "window": 3600},  # 50 per hour
        "dashboard_data": {"requests": 200, "window": 3600},  # 200 per hour
        
        # Real-time streaming
        "websocket_connect": {"requests": 10, "window": 3600},  # 10 connections per hour
        "websocket_message": {"requests": 1000, "window": 3600},  # 1000 messages per hour
        
        # Health and monitoring (more permissive)
        "health": {"requests": 100, "window": 3600},  # 100 per hour
        "metrics": {"requests": 50, "window": 3600},  # 50 per hour
        
        # General API (default)
        "default": {"requests": 500, "window": 3600}  # 500 per hour
    }
    
    # Burst limiting (short-term higher limits)
    BURST_LIMITS = {
        "default": {"requests": 50, "window": 60},  # 50 per minute burst
        "agents_query": {"requests": 20, "window": 60},  # 20 queries per minute burst
        "trading_data": {"requests": 100, "window": 60}  # 100 data requests per minute burst
    }
    
    @classmethod
    def get_endpoint_config(cls, endpoint: str) -> Dict[str, int]:
        """Get rate limit config for endpoint"""
        # Find most specific match
        for pattern, config in cls.ENDPOINT_LIMITS.items():
            if pattern in endpoint or endpoint.endswith(pattern):
                return config
        
        return cls.ENDPOINT_LIMITS["default"]
    
    @classmethod
    def get_burst_config(cls, endpoint: str) -> Dict[str, int]:
        """Get burst limit config for endpoint"""
        for pattern, config in cls.BURST_LIMITS.items():
            if pattern in endpoint or endpoint.endswith(pattern):
                return config
        
        return cls.BURST_LIMITS["default"]

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, store: RateLimitStore = None):
        super().__init__(app)
        self.store = store or rate_limit_store
        self.cleanup_task = None
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        skip_paths = [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/favicon.ico"
        ]
        
        if request.url.path in skip_paths:
            response = await call_next(request)
            return response
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Get user identifier if available
        user_id = getattr(request.state, "user", None)
        user_identifier = f"user_{user_id.id}" if user_id else f"ip_{client_ip}"
        
        # Get endpoint type
        endpoint_type = self._get_endpoint_type(request.url.path)
        
        # Get rate limit configuration
        rate_config = RateLimitConfig.get_endpoint_config(endpoint_type)
        burst_config = RateLimitConfig.get_burst_config(endpoint_type)
        
        # Check main rate limit
        allowed_main, main_info = self.store.check_rate_limit(
            user_identifier, 
            f"main_{endpoint_type}",
            rate_config["requests"],
            rate_config["window"]
        )
        
        # Check burst rate limit
        allowed_burst, burst_info = self.store.check_rate_limit(
            user_identifier,
            f"burst_{endpoint_type}", 
            burst_config["requests"],
            burst_config["window"]
        )
        
        # Determine if request is allowed
        if not allowed_main:
            # Main rate limit exceeded
            return self._create_rate_limit_response(request, main_info, "main")
        
        # Request allowed, process it
        response = await call_next(request)
        
        # Add rate limit headers
        self._add_rate_limit_headers(response, main_info, burst_info)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type from path"""
        path_lower = path.lower()
        
        if "/auth" in path_lower or "/login" in path_lower:
            return "auth"
        elif "/agents" in path_lower:
            if "create" in path_lower or path_lower.endswith("/agents"):
                return "agents_create"
            elif "query" in path_lower:
                return "agents_query"  
            else:
                return "agents_status"
        elif "/trading" in path_lower or "/metrics" in path_lower:
            return "trading_metrics"
        elif "/workflows" in path_lower:
            if "create" in path_lower or path_lower.endswith("/workflows"):
                return "workflows_create"
            else:
                return "workflows_status"
        elif "/dashboard" in path_lower:
            if "config" in path_lower:
                return "dashboard_config"
            else:
                return "dashboard_data"
        elif "/ws" in path_lower or "websocket" in path_lower:
            if "connect" in path_lower:
                return "websocket_connect"
            else:
                return "websocket_message"
        elif "/health" in path_lower or "/metrics" in path_lower:
            return "health" if "/health" in path_lower else "metrics"
        else:
            return "default"
    
    def _create_rate_limit_response(self, request: Request, rate_info: Dict[str, Any], 
                                  limit_type: str) -> Response:
        """Create rate limit exceeded response"""
        retry_after = rate_info["retry_after"]
        
        response_data = {
            "error": {
                "code": 429,
                "type": "rate_limit_exceeded",
                "message": f"Rate limit exceeded ({limit_type} limit)",
                "details": {
                    "limit": rate_info["limit"],
                    "window_seconds": rate_info["window"],
                    "reset_time": datetime.fromtimestamp(rate_info["reset_time"]).isoformat(),
                    "retry_after_seconds": retry_after
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
        response = JSONResponse(
            status_code=429,
            content=response_data,
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(rate_info["reset_time"])),
                "X-RateLimit-Type": limit_type
            }
        )
        
        logger.warning(
            f"Rate limit exceeded for {request.url.path} "
            f"(limit: {rate_info['limit']}, window: {rate_info['window']}s)"
        )
        
        return response
    
    def _add_rate_limit_headers(self, response: Response, main_info: Dict[str, Any], 
                              burst_info: Dict[str, Any]):
        """Add rate limit headers to response"""
        response.headers["X-RateLimit-Limit"] = str(main_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(main_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(main_info["reset_time"]))
        response.headers["X-RateLimit-Burst-Limit"] = str(burst_info["limit"])
        response.headers["X-RateLimit-Burst-Remaining"] = str(burst_info["remaining"])

# Global middleware instance
rate_limiter_middleware = RateLimitMiddleware

# Rate limit utilities
def get_user_rate_limit(user_tier: str) -> Dict[str, int]:
    """Get rate limit configuration for user tier"""
    base_config = RateLimitConfig.ENDPOINT_LIMITS["default"]
    
    # Scale limits based on user tier
    tier_multipliers = {
        "default": 1.0,
        "premium": 5.0,  # 5x higher limits
        "enterprise": 10.0  # 10x higher limits
    }
    
    multiplier = tier_multipliers.get(user_tier, 1.0)
    
    return {
        "requests": int(base_config["requests"] * multiplier),
        "window": base_config["window"]
    }

def check_rate_limit(identifier: str, endpoint: str, user_tier: str = "default") -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for identifier and endpoint"""
    config = get_user_rate_limit(user_tier)
    
    return rate_limit_store.check_rate_limit(
        identifier, endpoint, config["requests"], config["window"]
    )

def get_rate_limit_stats() -> Dict[str, Any]:
    """Get rate limiting statistics"""
    current_time = time.time()
    total_entries = len(rate_limit_store._limits)
    
    active_entries = 0
    total_requests = 0
    
    for key, rate_data in rate_limit_store._limits.items():
        request_times = rate_data["requests"]
        if request_times:
            active_entries += 1
            total_requests += len(request_times)
    
    return {
        "total_entries": total_entries,
        "active_entries": active_entries,
        "total_requests_tracked": total_requests,
        "cleanup_interval_seconds": rate_limit_store._cleanup_interval,
        "last_cleanup": datetime.fromtimestamp(rate_limit_store._last_cleanup).isoformat(),
        "timestamp": datetime.now().isoformat()
    }

async def start_rate_limit_cleanup():
    """Start background rate limit cleanup task"""
    while True:
        try:
            await asyncio.sleep(rate_limit_store._cleanup_interval)
            rate_limit_store.cleanup_old_entries()
            logger.debug("Rate limit store cleaned up")
        except Exception as e:
            logger.error(f"Rate limit cleanup error: {e}")

# Export middleware and utilities
__all__ = [
    "RateLimitMiddleware",
    "rate_limit_store", 
    "get_user_rate_limit",
    "check_rate_limit",
    "get_rate_limit_stats",
    "start_rate_limit_cleanup"
]