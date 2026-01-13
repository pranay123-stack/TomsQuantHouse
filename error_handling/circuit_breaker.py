"""
Circuit Breaker Pattern for Service Resilience
"""
import time
import asyncio
from enum import Enum
from typing import Callable, Any, Optional, List
from dataclasses import dataclass, field
from threading import Lock
import logging
from .error_types import StructuredError, ErrorContext


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class FailureMode(Enum):
    """Circuit breaker failure detection modes"""
    COUNT_BASED = "count_based"      # Based on failure count
    TIME_BASED = "time_based"        # Based on time window
    PERCENTAGE_BASED = "percentage_based"  # Based on failure percentage


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5              # Number of failures to open circuit
    success_threshold: int = 3              # Successes needed to close from half-open
    timeout: float = 60.0                   # Seconds before trying half-open
    window_size: int = 100                  # Size of rolling window for metrics
    failure_percentage_threshold: float = 50.0  # Percentage threshold for failure
    timeout_threshold: int = 3              # Timeout failures to open circuit
    slow_call_duration_threshold: float = 5.0  # Threshold for slow call (seconds)
    slow_call_rate_threshold: float = 50.0  # Percentage of slow calls to open circuit
    failure_mode: FailureMode = FailureMode.COUNT_BASED
    reset_timeout: float = 60.0             # Time to wait before half-open (alias for timeout)


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker state monitoring"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    slow_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_transitions: List[tuple] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_calls == 0:
            return 100.0
        return (self.successful_calls / self.total_calls) * 100
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        if self.total_calls == 0:
            return 0.0
        return (self.failed_calls / self.total_calls) * 100
    
    @property
    def slow_call_rate(self) -> float:
        """Calculate slow call rate percentage"""
        if self.total_calls == 0:
            return 0.0
        return (self.slow_calls / self.total_calls) * 100


class CircuitBreaker:
    """Circuit breaker implementation with multiple failure detection modes"""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = Lock()
        self._half_open_attempts = 0
        self._half_open_start_time = None
        self.logger = logger or logging.getLogger(f"circuit_breaker.{name}")
        
        # Ensure backward compatibility
        if self.config.reset_timeout and self.config.timeout == CircuitBreakerConfig().timeout:
            self.config.timeout = self.config.reset_timeout
    
    def _record_call(self, success: bool, duration: float = 0.0, timeout: bool = False):
        """Record a call attempt"""
        with self._lock:
            self.metrics.total_calls += 1
            
            if success:
                self.metrics.successful_calls += 1
                self.metrics.last_success_time = time.time()
            else:
                self.metrics.failed_calls += 1
                self.metrics.last_failure_time = time.time()
            
            if timeout:
                self.metrics.timeout_calls += 1
            
            if duration >= self.config.slow_call_duration_threshold:
                self.metrics.slow_calls += 1
    
    def _should_open(self) -> bool:
        """Determine if circuit breaker should open based on current metrics"""
        mode = self.config.failure_mode
        
        if mode == FailureMode.COUNT_BASED:
            return self.metrics.failed_calls >= self.config.failure_threshold
        
        elif mode == FailureMode.TIME_BASED:
            if not self.metrics.last_failure_time:
                return False
            time_since_failure = time.time() - self.metrics.last_failure_time
            return time_since_failure < self.config.timeout
        
        elif mode == FailureMode.PERCENTAGE_BASED:
            if self.metrics.total_calls < self.config.window_size:
                return False
            return self.metrics.failure_rate >= self.config.failure_percentage_threshold
        
        return False
    
    def _should_close_from_half_open(self) -> bool:
        """Determine if circuit breaker should close from half-open state"""
        if self._half_open_attempts >= self.config.success_threshold:
            return True
        return False
    
    def _transition_to(self, new_state: CircuitBreakerState):
        """Transition to a new state"""
        old_state = self.state
        self.state = new_state
        transition_time = time.time()
        
        self.metrics.state_transitions.append((old_state.value, new_state.value, transition_time))
        
        self.logger.info(
            f"Circuit breaker '{self.name}' transitioned from {old_state.value} to {new_state.value}"
        )
        
        if new_state == CircuitBreakerState.HALF_OPEN:
            self._half_open_start_time = time.time()
            self._half_open_attempts = 0
        elif new_state == CircuitBreakerState.CLOSED:
            # Reset metrics when closing
            self._reset_metrics()
    
    def _reset_metrics(self):
        """Reset circuit breaker metrics"""
        self.metrics = CircuitBreakerMetrics()
        self._half_open_attempts = 0
        self._half_open_start_time = None
    
    def _check_timeout(self) -> bool:
        """Check if timeout for half-open state has elapsed"""
        if (self.state == CircuitBreakerState.OPEN and 
            self._half_open_start_time and
            time.time() - self._half_open_start_time >= self.config.timeout):
            return True
        return False
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker (sync version)"""
        start_time = time.time()
        
        # Check if we should transition from open to half-open
        if self.state == CircuitBreakerState.OPEN and self._check_timeout():
            self._transition_to(CircuitBreakerState.HALF_OPEN)
        
        # Check if circuit is open
        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN",
                self.name,
                self.state
            )
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record successful call
            self._record_call(success=True, duration=duration)
            
            # Handle state transitions
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._half_open_attempts += 1
                if self._half_open_attempts >= self.config.success_threshold:
                    self._transition_to(CircuitBreakerState.CLOSED)
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success if we're tracking failures
                if self.metrics.failed_calls > 0:
                    self._reset_metrics()
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            is_timeout = isinstance(e, TimeoutError)
            
            # Record failed call
            self._record_call(success=False, duration=duration, timeout=is_timeout)
            
            # Check if we should open the circuit
            if self._should_open():
                self._transition_to(CircuitBreakerState.OPEN)
            
            # For half-open state, increment attempt counter
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._half_open_attempts += 1
                # If we fail in half-open, go back to open
                self._transition_to(CircuitBreakerState.OPEN)
            
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker (async version)"""
        start_time = time.time()
        
        # Check if we should transition from open to half-open
        if self.state == CircuitBreakerState.OPEN and self._check_timeout():
            self._transition_to(CircuitBreakerState.HALF_OPEN)
        
        # Check if circuit is open
        if self.state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN",
                self.name,
                self.state
            )
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            
            # Record successful call
            self._record_call(success=True, duration=duration)
            
            # Handle state transitions
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._half_open_attempts += 1
                if self._half_open_attempts >= self.config.success_threshold:
                    self._transition_to(CircuitBreakerState.CLOSED)
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                if self.metrics.failed_calls > 0:
                    self._reset_metrics()
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            is_timeout = isinstance(e, TimeoutError)
            
            # Record failed call
            self._record_call(success=False, duration=duration, timeout=is_timeout)
            
            # Check if we should open the circuit
            if self._should_open():
                self._transition_to(CircuitBreakerState.OPEN)
            
            # For half-open state, increment attempt counter
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._half_open_attempts += 1
                # If we fail in half-open, go back to open
                self._transition_to(CircuitBreakerState.OPEN)
            
            raise e
    
    def record_success(self):
        """Manually record a successful operation"""
        self._record_call(success=True)
        
        # If we're in half-open and have enough successes, close the circuit
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_attempts += 1
            if self._half_open_attempts >= self.config.success_threshold:
                self._transition_to(CircuitBreakerState.CLOSED)
    
    def record_failure(self):
        """Manually record a failed operation"""
        self._record_call(success=False)
        
        # Check if we should open the circuit
        if self._should_open():
            self._transition_to(CircuitBreakerState.OPEN)
        
        # If we're in half-open and fail, go back to open
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_attempts += 1
            self._transition_to(CircuitBreakerState.OPEN)
    
    def get_state(self) -> dict:
        """Get current circuit breaker state and metrics"""
        return {
            'name': self.name,
            'state': self.state.value,
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'success_threshold': self.config.success_threshold,
                'timeout': self.config.timeout,
                'failure_mode': self.config.failure_mode.value
            },
            'metrics': {
                'total_calls': self.metrics.total_calls,
                'successful_calls': self.metrics.successful_calls,
                'failed_calls': self.metrics.failed_calls,
                'timeout_calls': self.metrics.timeout_calls,
                'slow_calls': self.metrics.slow_calls,
                'success_rate': self.metrics.success_rate,
                'failure_rate': self.metrics.failure_rate,
                'slow_call_rate': self.metrics.slow_call_rate,
                'last_failure_time': self.metrics.last_failure_time,
                'last_success_time': self.metrics.last_success_time
            },
            'half_open_attempts': self._half_open_attempts,
            'state_transitions': self.metrics.state_transitions[-5:]  # Last 5 transitions
        }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        with self._lock:
            self.state = CircuitBreakerState.CLOSED
            self._reset_metrics()
            self.logger.info(f"Circuit breaker '{self.name}' has been reset")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    
    def __init__(self, message: str, name: str, state: CircuitBreakerState):
        super().__init__(message)
        self.name = name
        self.state = state


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self):
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._lock = Lock()
    
    def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get existing circuit breaker or create a new one"""
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(name, config)
            return self._circuit_breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self._circuit_breakers.get(name)
    
    def remove(self, name: str):
        """Remove circuit breaker from registry"""
        with self._lock:
            if name in self._circuit_breakers:
                del self._circuit_breakers[name]
    
    def get_all_states(self) -> dict:
        """Get state of all circuit breakers"""
        return {name: cb.get_state() for name, cb in self._circuit_breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for cb in self._circuit_breakers.values():
            cb.reset()


# Default registry instance
default_registry = CircuitBreakerRegistry()


# Decorators for circuit breaker protection
def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    registry: Optional[CircuitBreakerRegistry] = None
):
    """Decorator to protect function with circuit breaker"""
    def decorator(func):
        cb_registry = registry or default_registry
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            circuit_breaker = cb_registry.get_or_create(name, config)
            return circuit_breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            circuit_breaker = cb_registry.get_or_create(name, config)
            return await circuit_breaker.call_async(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


# Pre-configured circuit breakers for common use cases
STRICT_CIRCUIT_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    timeout=30.0,
    success_threshold=2,
    failure_mode=FailureMode.COUNT_BASED
)

LENIENT_CIRCUIT_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=10,
    timeout=120.0,
    success_threshold=5,
    failure_mode=FailureMode.PERCENTAGE_BASED,
    window_size=50,
    failure_percentage_threshold=80.0
)

SLOW_CIRCUIT_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    slow_call_duration_threshold=2.0,
    slow_call_rate_threshold=30.0,
    failure_mode=FailureMode.PERCENTAGE_BASED
)