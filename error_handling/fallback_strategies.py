"""
Fallback Strategies for Degraded Service Functionality
"""
import asyncio
import logging
from typing import Any, Callable, Optional, Dict, List, Union, Awaitable
from enum import Enum
from dataclasses import dataclass
from functools import wraps
from .error_types import StructuredError, ErrorContext
from .circuit_breaker import CircuitBreaker


class FallbackType(Enum):
    """Types of fallback strategies"""
    DEFAULT_VALUE = "default_value"
    CACHE_FALLBACK = "cache_fallback"
    STATIC_DATA = "static_data"
    REMOTE_FALLBACK = "remote_fallback"
    BUFFERED_DATA = "buffered_data"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    COMPENSATING_ACTION = "compensating_action"


class FallbackStrategy(Enum):
    """Fallback execution strategies"""
    IMMEDIATE = "immediate"        # Execute fallback immediately on failure
    CASCADE = "cascade"            # Try fallbacks in sequence
    PARALLEL = "parallel"          # Try fallbacks in parallel
    CONDITIONAL = "conditional"     # Use conditional logic to choose fallback


@dataclass
class FallbackConfig:
    """Configuration for fallback strategies"""
    strategy: FallbackStrategy = FallbackStrategy.CASCADE
    timeout: float = 10.0
    retry_count: int = 1
    cache_ttl: int = 300  # Cache time-to-live in seconds
    enable_logging: bool = True
    fallback_order: Optional[List[str]] = None


class FallbackResult:
    """Result of fallback operation"""
    
    def __init__(
        self,
        success: bool,
        data: Any = None,
        fallback_used: Optional[str] = None,
        error: Optional[Exception] = None,
        source: str = "primary"
    ):
        self.success = success
        self.data = data
        self.fallback_used = fallback_used
        self.error = error
        self.source = source
        self.timestamp = asyncio.get_event_loop().time()
    
    def __repr__(self):
        return f"FallbackResult(success={self.success}, source={self.source}, fallback={self.fallback_used})"


class CacheFallback:
    """Cache-based fallback strategy"""
    
    def __init__(self, cache_provider: Callable[[], Dict], ttl: int = 300):
        self.cache_provider = cache_provider
        self.ttl = ttl
        self.logger = logging.getLogger("fallback.cache")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from cache fallback"""
        try:
            cache = self.cache_provider()
            if key in cache:
                data, timestamp = cache[key]
                if asyncio.get_event_loop().time() - timestamp < self.ttl:
                    self.logger.info(f"Cache hit for key: {key}")
                    return data
                else:
                    self.logger.warning(f"Cache expired for key: {key}")
        except Exception as e:
            self.logger.error(f"Cache fallback failed: {e}")
        return None
    
    async def set(self, key: str, value: Any):
        """Set data in cache fallback"""
        try:
            cache = self.cache_provider()
            cache[key] = (value, asyncio.get_event_loop().time())
            self.logger.info(f"Cached value for key: {key}")
        except Exception as e:
            self.logger.error(f"Cache set failed: {e}")


class StaticDataFallback:
    """Static data fallback strategy"""
    
    def __init__(self, static_data: Dict[str, Any]):
        self.static_data = static_data
        self.logger = logging.getLogger("fallback.static")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from static fallback"""
        try:
            if key in self.static_data:
                self.logger.info(f"Static data hit for key: {key}")
                return self.static_data[key]
        except Exception as e:
            self.logger.error(f"Static data fallback failed: {e}")
        return None


class RemoteFallback:
    """Remote service fallback strategy"""
    
    def __init__(self, fallback_service: Callable, timeout: float = 10.0):
        self.fallback_service = fallback_service
        self.timeout = timeout
        self.logger = logging.getLogger("fallback.remote")
    
    async def call(self, *args, **kwargs) -> Any:
        """Call remote fallback service"""
        try:
            if asyncio.iscoroutinefunction(self.fallback_service):
                return await asyncio.wait_for(self.fallback_service(*args, **kwargs), timeout=self.timeout)
            else:
                return await asyncio.wait_for(
                    asyncio.to_thread(self.fallback_service, *args, **kwargs),
                    timeout=self.timeout
                )
        except Exception as e:
            self.logger.error(f"Remote fallback failed: {e}")
            raise


class GracefulDegradation:
    """Graceful degradation fallback strategy"""
    
    def __init__(self, degradation_levels: Dict[str, Callable]):
        self.degradation_levels = degradation_levels
        self.current_level = "full_functionality"
        self.logger = logging.getLogger("fallback.degradation")
    
    def set_level(self, level: str):
        """Set degradation level"""
        if level in self.degradation_levels:
            self.current_level = level
            self.logger.info(f"Set degradation level to: {level}")
        else:
            self.logger.warning(f"Unknown degradation level: {level}")
    
    async def execute(self, *args, **kwargs) -> Any:
        """Execute function at current degradation level"""
        try:
            func = self.degradation_levels.get(self.current_level)
            if func:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            else:
                raise ValueError(f"No function available for level: {self.current_level}")
        except Exception as e:
            self.logger.error(f"Graceful degradation failed: {e}")
            raise


class FallbackManager:
    """Manages multiple fallback strategies"""
    
    def __init__(self, config: Optional[FallbackConfig] = None):
        self.config = config or FallbackConfig()
        self.fallbacks: Dict[str, Callable] = {}
        self.logger = logging.getLogger("fallback.manager")
        
        # Register built-in fallbacks
        self.register("default", self._default_fallback)
    
    def register(self, name: str, fallback_func: Callable):
        """Register a fallback function"""
        self.fallbacks[name] = fallback_func
        self.logger.debug(f"Registered fallback: {name}")
    
    def unregister(self, name: str):
        """Unregister a fallback function"""
        if name in self.fallbacks:
            del self.fallbacks[name]
            self.logger.debug(f"Unregistered fallback: {name}")
    
    async def execute_fallback(
        self,
        primary_func: Callable,
        fallback_names: Optional[List[str]] = None,
        *args,
        **kwargs
    ) -> FallbackResult:
        """Execute primary function with fallback strategies"""
        
        if not fallback_names:
            fallback_names = list(self.fallbacks.keys())
        
        try:
            # Try primary function first
            if asyncio.iscoroutinefunction(primary_func):
                result = await primary_func(*args, **kwargs)
            else:
                result = await asyncio.to_thread(primary_func, *args, **kwargs)
            
            return FallbackResult(success=True, data=result, source="primary")
            
        except Exception as e:
            self.logger.warning(f"Primary function failed: {e}")
            
            if self.config.strategy == FallbackStrategy.IMMEDIATE:
                return await self._execute_single_fallback(fallback_names[0], *args, **kwargs)
            
            elif self.config.strategy == FallbackStrategy.CASCADE:
                return await self._execute_cascade_fallback(fallback_names, *args, **kwargs)
            
            elif self.config.strategy == FallbackStrategy.PARALLEL:
                return await self._execute_parallel_fallback(fallback_names, *args, **kwargs)
            
            else:
                return FallbackResult(success=False, error=e, source="none")
    
    async def _execute_single_fallback(self, fallback_name: str, *args, **kwargs) -> FallbackResult:
        """Execute a single fallback function"""
        try:
            fallback_func = self.fallbacks[fallback_name]
            if asyncio.iscoroutinefunction(fallback_func):
                result = await fallback_func(*args, **kwargs)
            else:
                result = await asyncio.to_thread(fallback_func, *args, **kwargs)
            
            return FallbackResult(success=True, data=result, fallback_used=fallback_name, source="fallback")
            
        except Exception as e:
            self.logger.error(f"Fallback '{fallback_name}' failed: {e}")
            return FallbackResult(success=False, error=e, source=fallback_name)
    
    async def _execute_cascade_fallback(self, fallback_names: List[str], *args, **kwargs) -> FallbackResult:
        """Execute fallback functions in sequence"""
        for fallback_name in fallback_names:
            result = await self._execute_single_fallback(fallback_name, *args, **kwargs)
            if result.success:
                return result
        
        return FallbackResult(success=False, error=Exception("All fallbacks failed"), source="none")
    
    async def _execute_parallel_fallback(self, fallback_names: List[str], *args, **kwargs) -> FallbackResult:
        """Execute fallback functions in parallel"""
        tasks = []
        for fallback_name in fallback_names:
            task = asyncio.create_task(self._execute_single_fallback(fallback_name, *args, **kwargs))
            tasks.append((fallback_name, task))
        
        # Wait for first successful result or all to fail
        results = []
        for fallback_name, task in tasks:
            try:
                result = await task
                results.append(result)
                if result.success:
                    self.logger.info(f"Parallel fallback '{fallback_name}' succeeded")
                    return result
            except Exception as e:
                self.logger.error(f"Parallel fallback '{fallback_name}' failed: {e}")
                results.append(FallbackResult(success=False, error=e, source=fallback_name))
        
        return FallbackResult(success=False, error=Exception("All parallel fallbacks failed"), source="none")
    
    async def _default_fallback(self, *args, **kwargs) -> Any:
        """Default fallback function"""
        return None


# Decorator for automatic fallback
def with_fallback(
    fallback_manager: Optional[FallbackManager] = None,
    fallback_names: Optional[List[str]] = None,
    config: Optional[FallbackConfig] = None
):
    """Decorator to add fallback support to functions"""
    def decorator(func):
        fm = fallback_manager or FallbackManager(config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await fm.execute_fallback(func, fallback_names, *args, **kwargs)
            if result.success:
                return result.data
            else:
                # Re-raise the original error or fallback error
                if result.error:
                    raise result.error
                raise Exception("All functions and fallbacks failed")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Convert to async for consistency
            return asyncio.run(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Circuit breaker integration with fallbacks
class CircuitBreakerWithFallback:
    """Circuit breaker with integrated fallback strategies"""
    
    def __init__(
        self,
        circuit_breaker: CircuitBreaker,
        fallback_manager: FallbackManager,
        fallback_on_circuit_open: bool = True
    ):
        self.circuit_breaker = circuit_breaker
        self.fallback_manager = fallback_manager
        self.fallback_on_circuit_open = fallback_on_circuit_open
        self.logger = logging.getLogger("cb_fallback")
    
    async def call_with_fallback(
        self,
        func: Callable,
        fallback_names: Optional[List[str]] = None,
        *args,
        **kwargs
    ) -> FallbackResult:
        """Call function through circuit breaker with fallback support"""
        
        try:
            # Try through circuit breaker
            result = await self.circuit_breaker.call_async(func, *args, **kwargs)
            return FallbackResult(success=True, data=result, source="circuit_breaker")
            
        except Exception as e:
            self.logger.warning(f"Circuit breaker call failed: {e}")
            
            # Check if circuit breaker is open
            if (self.fallback_on_circuit_open and 
                hasattr(e, 'state') and e.state.value == "open"):
                
                return await self.fallback_manager.execute_fallback(
                    func, fallback_names, *args, **kwargs
                )
            
            # Try regular fallback
            return await self.fallback_manager.execute_fallback(
                func, fallback_names, *args, **kwargs
            )


# Pre-configured fallback managers
DEFAULT_FALLBACK_MANAGER = FallbackManager(
    config=FallbackConfig(
        strategy=FallbackStrategy.CASCADE,
        timeout=5.0,
        retry_count=2
    )
)

PARALLEL_FALLBACK_MANAGER = FallbackManager(
    config=FallbackConfig(
        strategy=FallbackStrategy.PARALLEL,
        timeout=10.0
    )
)

# Common fallback functions
async def cache_fallback(*args, **kwargs) -> Dict[str, Any]:
    """Cache fallback example"""
    return {"data": "from_cache", "timestamp": asyncio.get_event_loop().time()}


async def static_fallback(*args, **kwargs) -> Dict[str, Any]:
    """Static data fallback example"""
    return {"data": "from_static", "status": "fallback"}


async def empty_response_fallback(*args, **kwargs) -> List:
    """Empty response fallback"""
    return []


async def default_value_fallback(*args, default=None, **kwargs) -> Any:
    """Default value fallback"""
    return default


# Example usage patterns
class ServiceWithFallback:
    """Example service with multiple fallback strategies"""
    
    def __init__(self):
        self.fallback_manager = DEFAULT_FALLBACK_MANAGER
        self.cache = {}
        
        # Register fallbacks
        self.fallback_manager.register("cache", self._cache_fallback)
        self.fallback_manager.register("static", self._static_fallback)
    
    async def _cache_fallback(self, key: str) -> Any:
        """Cache fallback implementation"""
        return self.cache.get(key, "cached_default")
    
    async def _static_fallback(self, key: str) -> Any:
        """Static fallback implementation"""
        static_data = {"user_info": {"name": "Default User"}, "settings": {}}
        return static_data.get(key, "static_default")
    
    @with_fallback(fallback_names=["cache", "static"])
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user data with fallback support"""
        # Simulate primary service call
        if user_id == "fail":
            raise Exception("Primary service failed")
        return {"id": user_id, "name": f"User {user_id}"}
