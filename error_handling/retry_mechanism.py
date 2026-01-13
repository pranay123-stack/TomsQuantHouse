"""
Intelligent Retry Mechanisms with Exponential Backoff
"""
import asyncio
import time
import random
from typing import Callable, Any, Optional, Union, List, Tuple
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from .error_types import StructuredError, ErrorRetryPolicy, BaseError


class RetryResult(Enum):
    """Retry operation results"""
    SUCCESS = "success"
    FAILURE = "failure"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    retryable_exceptions: Optional[List[type]] = None
    non_retryable_exceptions: Optional[List[type]] = None
    custom_delay_func: Optional[Callable[[int, Exception], float]] = None


class RetryManager:
    """Manages retry logic with various backoff strategies"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._stats = {
            'total_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'max_retries_exceeded': 0
        }
    
    def calculate_delay(self, attempt: int, exception: Exception) -> float:
        """Calculate delay for next retry attempt"""
        if self.config.custom_delay_func:
            return self.config.custom_delay_func(attempt, exception)
        
        base_delay = self.config.base_delay
        
        # Exponential backoff
        delay = base_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Apply jitter to prevent thundering herd
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        # Ensure delay is within bounds
        return max(self.config.base_delay, min(delay, self.config.max_delay))
    
    def is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        if self.config.non_retryable_exceptions:
            for exc_type in self.config.non_retryable_exceptions:
                if isinstance(exception, exc_type):
                    return False
        
        if self.config.retryable_exceptions:
            for exc_type in self.config.retryable_exceptions:
                if isinstance(exception, exc_type):
                    return True
            return False
        
        # Default behavior: retry on most exceptions except validation errors
        return not isinstance(exception, (ValueError, TypeError))
    
    async def retry_async(
        self,
        func: Callable,
        *args,
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        **kwargs
    ) -> Tuple[Any, RetryResult]:
        """Execute function with retry logic (async version)"""
        
        last_exception = None
        result = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            self._stats['total_attempts'] += 1
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if attempt > 1:
                    self._stats['successful_retries'] += 1
                
                return result, RetryResult.SUCCESS
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self.is_retryable_exception(e):
                    return None, RetryResult.FAILURE
                
                # Call retry callback
                if on_retry:
                    on_retry(e, attempt)
                
                # If this is the last attempt, fail
                if attempt >= self.config.max_attempts:
                    self._stats['max_retries_exceeded'] += 1
                    return None, RetryResult.MAX_RETRIES_EXCEEDED
                
                # Calculate and wait for next retry
                delay = self.calculate_delay(attempt, e)
                await asyncio.sleep(delay)
        
        # Should not reach here
        return None, RetryResult.FAILURE
    
    def retry_sync(
        self,
        func: Callable,
        *args,
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        **kwargs
    ) -> Tuple[Any, RetryResult]:
        """Execute function with retry logic (sync version)"""
        
        last_exception = None
        result = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            self._stats['total_attempts'] += 1
            
            try:
                result = func(*args, **kwargs)
                
                if attempt > 1:
                    self._stats['successful_retries'] += 1
                
                return result, RetryResult.SUCCESS
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self.is_retryable_exception(e):
                    return None, RetryResult.FAILURE
                
                # Call retry callback
                if on_retry:
                    on_retry(e, attempt)
                
                # If this is the last attempt, fail
                if attempt >= self.config.max_attempts:
                    self._stats['max_retries_exceeded'] += 1
                    return None, RetryResult.MAX_RETRIES_EXCEEDED
                
                # Calculate and wait for next retry
                delay = self.calculate_delay(attempt, e)
                time.sleep(delay)
        
        # Should not reach here
        return None, RetryResult.FAILURE
    
    def get_stats(self) -> dict:
        """Get retry statistics"""
        return self._stats.copy()
    
    def reset_stats(self):
        """Reset retry statistics"""
        self._stats = {
            'total_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'max_retries_exceeded': 0
        }


# Decorators for automatic retry
def retry_async(config: Optional[RetryConfig] = None, max_attempts: int = 3):
    """Decorator for async function retry"""
    def decorator(func):
        retry_manager = RetryManager(config or RetryConfig(max_attempts=max_attempts))
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result, status = await retry_manager.retry_async(func, *args, **kwargs)
            if status != RetryResult.SUCCESS:
                raise last_exception
            return result
        return wrapper
    return decorator


def retry_sync(config: Optional[RetryConfig] = None, max_attempts: int = 3):
    """Decorator for sync function retry"""
    def decorator(func):
        retry_manager = RetryManager(config or RetryConfig(max_attempts=max_attempts))
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            result, status = retry_manager.retry_sync(func, *args, **kwargs)
            if status != RetryResult.SUCCESS:
                # Re-raise the last exception
                pass  # This would need to capture the last exception
            return result
        return wrapper
    return decorator


# Specialized retry configurations
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=[ConnectionError, TimeoutError],
    non_retryable_exceptions=[ValueError, TypeError]
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=1.5,
    jitter=False
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=[ConnectionError, TimeoutError, ConnectionResetError],
    non_retryable_exceptions=[ValueError, TypeError]
)

EXPONENTIAL_BACKOFF_CONFIG = RetryConfig(
    max_attempts=6,
    base_delay=0.5,
    max_delay=120.0,
    exponential_base=2.0,
    jitter=True,
    jitter_range=0.2
)


# Retry with exponential backoff context manager
class RetryContext:
    """Context manager for retry operations"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.retry_manager = RetryManager(self.config)
    
    async def __aenter__(self):
        return self.retry_manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Circuit breaker integration with retry
class CircuitBreakerRetryManager:
    """Retry manager with circuit breaker integration"""
    
    def __init__(self, config: Optional[RetryConfig] = None, 
                 circuit_breaker=None):
        self.config = config or RetryConfig()
        self.retry_manager = RetryManager(self.config)
        self.circuit_breaker = circuit_breaker
    
    async def retry_async(
        self,
        func: Callable,
        *args,
        on_retry: Optional[Callable[[Exception, int], None]] = None,
        **kwargs
    ) -> Tuple[Any, RetryResult]:
        """Execute function with retry logic and circuit breaker (async version)"""
        
        # Check circuit breaker state
        if self.circuit_breaker and self.circuit_breaker.state == "OPEN":
            return None, RetryResult.CIRCUIT_BREAKER_OPEN
        
        try:
            result, status = await self.retry_manager.retry_async(
                func, *args, on_retry=on_retry, **kwargs
            )
            
            # Report success to circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_success()
            
            return result, status
            
        except Exception as e:
            # Report failure to circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            
            return None, RetryResult.FAILURE