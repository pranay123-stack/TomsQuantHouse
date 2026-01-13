"""
Error Handling System - Main Integration Module

This module provides a unified interface to all error handling components:
- Structured error types
- Retry mechanisms with exponential backoff
- Circuit breaker patterns
- Fallback strategies
- Error logging with correlation tracking
- Health checks with automated recovery
- Graceful degradation
- Error dashboard and monitoring alerts
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import asynccontextmanager
import json

# Import all components
from .error_types import (
    StructuredError, ErrorCategory, ErrorSeverity, ErrorContext,
    NetworkError, DatabaseError, APIError, ValidationError,
    TimeoutError, RateLimitError, SystemError, create_error_from_exception
)

from .retry_mechanism import (
    RetryManager, RetryConfig, RetryResult, RetryContext,
    NETWORK_RETRY_CONFIG, DATABASE_RETRY_CONFIG, API_RETRY_CONFIG
)

from .circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    FailureMode, default_registry, circuit_breaker,
    STRICT_CIRCUIT_BREAKER_CONFIG, LENIENT_CIRCUIT_BREAKER_CONFIG
)

from .fallback_strategies import (
    FallbackManager, FallbackConfig, FallbackStrategy, FallbackResult,
    CacheFallback, StaticDataFallback, RemoteFallback, GracefulDegradation,
    DEFAULT_FALLBACK_MANAGER, with_fallback
)

from .error_logging import (
    ErrorLogger, LogContext, CorrelationContext, TracingLogger,
    global_error_logger, tracing_logger, with_logging,
    error_context, extract_correlation_id, inject_correlation_id
)

from .health_checks import (
    HealthChecker, HealthCheckManager, HealthStatus, CheckType,
    HealthCheckConfig, HTTPHealthChecker, DatabaseHealthChecker,
    CustomHealthChecker, ResourceHealthChecker, default_health_manager,
    health_checkable, restart_service_action, clear_cache_action
)

from .graceful_degradation import (
    GracefulDegradationManager, DegradationLevel, ServiceTier, ServiceInfo,
    ServiceProxy, CapacityManager, FeatureFlags,
    default_degradation_manager, default_service_proxy,
    graceful_degradation
)

from .error_dashboard import (
    AlertManager, AlertRule, Alert, AlertSeverity, MetricStore,
    ErrorDashboard, default_metric_store, default_alert_manager,
    default_dashboard, dashboard_context, create_default_alert_rules
)


class ErrorHandlingSystem:
    """
    Unified Error Handling System
    
    This class integrates all error handling components into a cohesive system
    with centralized configuration and management.
    """
    
    def __init__(
        self,
        service_name: str = "default_service",
        config: Optional[Dict[str, Any]] = None
    ):
        self.service_name = service_name
        self.config = config or {}
        
        # Initialize logging
        self.logger = logging.getLogger(f"error_system.{service_name}")
        
        # Initialize core components
        self.error_logger = global_error_logger
        self.health_manager = default_health_manager
        self.degradation_manager = default_degradation_manager
        self.alert_manager = default_alert_manager
        self.dashboard = default_dashboard
        
        # Initialize managers
        self.circuit_breaker_registry = default_registry
        self.fallback_manager = DEFAULT_FALLBACK_MANAGER
        
        # Tracking and monitoring
        self.tracing_logger = TracingLogger(service_name, self.error_logger)
        
        # State
        self._initialized = False
        self._monitoring_active = False
    
    async def initialize(self, custom_config: Optional[Dict[str, Any]] = None):
        """Initialize the error handling system"""
        if self._initialized:
            return
        
        config = custom_config or self.config
        
        self.logger.info(f"Initializing error handling system for {self.service_name}")
        
        # Setup health checks
        await self._setup_health_checks(config.get('health_checks', {}))
        
        # Setup circuit breakers
        self._setup_circuit_breakers(config.get('circuit_breakers', {}))
        
        # Setup fallback strategies
        self._setup_fallback_strategies(config.get('fallbacks', {}))
        
        # Setup graceful degradation
        await self._setup_graceful_degradation(config.get('degradation', {}))
        
        # Setup alert rules
        self._setup_alert_rules(config.get('alerts', {}))
        
        # Start monitoring
        await self.start_monitoring()
        
        self._initialized = True
        self.logger.info("Error handling system initialized successfully")
    
    async def start_monitoring(self):
        """Start all monitoring and alerting"""
        if self._monitoring_active:
            return
        
        self.logger.info("Starting error handling monitoring")
        
        # Start health monitoring
        await self.health_manager.start_monitoring()
        
        # Start alert monitoring
        await self.alert_manager.start_monitoring()
        
        # Start degradation monitoring
        await self._start_degradation_monitoring()
        
        self._monitoring_active = True
    
    async def stop_monitoring(self):
        """Stop all monitoring and alerting"""
        if not self._monitoring_active:
            return
        
        self.logger.info("Stopping error handling monitoring")
        
        # Stop health monitoring
        await self.health_manager.stop_monitoring()
        
        # Stop alert monitoring
        await self.alert_manager.stop_monitoring()
        
        self._monitoring_active = False
    
    async def _setup_health_checks(self, health_config: Dict[str, Any]):
        """Setup health checks based on configuration"""
        for check_config in health_config.get('checks', []):
            checker_type = check_config.get('type')
            
            if checker_type == 'http':
                checker = HTTPHealthChecker(
                    name=check_config['name'],
                    url=check_config['url'],
                    config=HealthCheckConfig(**check_config.get('config', {}))
                )
            elif checker_type == 'database':
                # This would need actual connection function
                checker = DatabaseHealthChecker(
                    name=check_config['name'],
                    connection_func=lambda: None,  # Placeholder
                    config=HealthCheckConfig(**check_config.get('config', {}))
                )
            elif checker_type == 'custom':
                # This would need actual check function
                checker = CustomHealthChecker(
                    name=check_config['name'],
                    check_func=lambda: True,  # Placeholder
                    config=HealthCheckConfig(**check_config.get('config', {}))
                )
            elif checker_type == 'resource':
                checker = ResourceHealthChecker(
                    name=check_config['name'],
                    config=HealthCheckConfig(**check_config.get('config', {}))
                )
            else:
                continue
            
            # Add recovery actions if specified
            for action_config in check_config.get('recovery_actions', []):
                action_type = action_config.get('type')
                if action_type == 'restart_service':
                    checker.add_recovery_action(
                        restart_service_action(action_config['service_name'])
                    )
                elif action_type == 'clear_cache':
                    checker.add_recovery_action(
                        clear_cache_action(action_config['cache_name'])
                    )
            
            self.health_manager.add_checker(checker)
    
    def _setup_circuit_breakers(self, cb_config: Dict[str, Any]):
        """Setup circuit breakers based on configuration"""
        for service_config in cb_config.get('services', []):
            service_name = service_config['name']
            config = CircuitBreakerConfig(**service_config.get('config', {}))
            
            self.circuit_breaker_registry.get_or_create(service_name, config)
    
    def _setup_fallback_strategies(self, fallback_config: Dict[str, Any]):
        """Setup fallback strategies"""
        # Register custom fallbacks
        for fallback_name, fallback_func in fallback_config.get('custom_fallbacks', {}).items():
            self.fallback_manager.register(fallback_name, fallback_func)
    
    async def _setup_graceful_degradation(self, degradation_config: Dict[str, Any]):
        """Setup graceful degradation"""
        # Register services
        for service_config in degradation_config.get('services', []):
            service_info = ServiceInfo(
                name=service_config['name'],
                tier=ServiceTier(service_config['tier']),
                description=service_config.get('description', ''),
                dependencies=service_config.get('dependencies', [])
            )
            self.degradation_manager.register_service(service_info)
        
        # Add degradation rules
        for rule_config in degradation_config.get('rules', []):
            from .graceful_degradation import DegradationRule
            rule = DegradationRule(
                trigger_condition=rule_config['condition'],
                target_level=DegradationLevel(rule_config['target_level']),
                services_to_disable=rule_config.get('services_to_disable', []),
                capacity_reduction=rule_config.get('capacity_reduction', 0.0),
                timeout_minutes=rule_config.get('timeout_minutes')
            )
            self.degradation_manager.add_degradation_rule(rule)
    
    def _setup_alert_rules(self, alert_config: Dict[str, Any]):
        """Setup alert rules"""
        # Clear existing rules
        for rule_name in list(self.alert_manager.alert_rules.keys()):
            self.alert_manager.remove_alert_rule(rule_name)
        
        # Add configured rules
        for rule_config in alert_config.get('rules', []):
            rule = AlertRule(
                name=rule_config['name'],
                condition=rule_config['condition'],
                severity=AlertSeverity(rule_config['severity']),
                description=rule_config['description'],
                notification_channels=rule_config.get('notification_channels', []),
                evaluation_interval=rule_config.get('evaluation_interval', 30),
                cooldown_period=rule_config.get('cooldown_period', 300)
            )
            self.alert_manager.add_alert_rule(rule)
    
    async def _start_degradation_monitoring(self):
        """Start degradation monitoring loop"""
        async def monitor_degradation():
            while self._monitoring_active:
                try:
                    # Collect metrics
                    metrics = await self._collect_system_metrics()
                    
                    # Evaluate degradation
                    target_level = await self.degradation_manager.evaluate_degradation(metrics)
                    
                    if target_level:
                        await self.degradation_manager.apply_degradation(
                            target_level, 
                            f"Degradation triggered by metrics: {metrics}"
                        )
                    
                    await asyncio.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    self.logger.error(f"Degradation monitoring error: {e}")
                    await asyncio.sleep(30)
        
        if self._monitoring_active:
            asyncio.create_task(monitor_degradation())
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system metrics for degradation evaluation"""
        metrics = {}
        
        # Health metrics
        health_data = self.health_manager.get_health_dashboard_data()
        metrics['overall_health_status'] = health_data.get('overall_status', 'unknown')
        metrics['total_checks'] = health_data.get('total_checks', 0)
        metrics['healthy_checks'] = sum(
            1 for checker in health_data.get('checkers', {}).values()
            if checker.get('status') == 'healthy'
        )
        
        # Error metrics
        error_stats = self.error_logger.get_error_stats()
        metrics['total_errors'] = error_stats.get('total_errors', 0)
        
        # Calculate error rate
        recent_errors = self.error_logger.get_recent_errors(limit=100)
        five_min_ago = asyncio.get_event_loop().time() - 300  # 5 minutes ago
        recent_error_count = sum(
            1 for error in recent_errors
            if hasattr(error, 'timestamp') and error.get('timestamp', '') >= str(five_min_ago)
        )
        metrics['error_rate'] = recent_error_count / 5.0  # errors per minute
        
        # Circuit breaker metrics
        cb_states = self.circuit_breaker_registry.get_all_states()
        metrics['circuit_breaker_failures'] = sum(
            state['metrics']['failed_calls'] for state in cb_states.values()
        )
        
        return metrics
    
    # Public API methods
    
    def create_error_context(
        self,
        operation_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogContext:
        """Create error context for tracing"""
        return LogContext(
            service_name=self.service_name,
            operation_name=operation_name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
    
    @asynccontextmanager
    async def error_context(
        self,
        operation_name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Context manager for error context"""
        context = self.create_error_context(operation_name, user_id, session_id, metadata)
        async with correlation_context.context(context):
            yield context
    
    async def execute_with_retry(
        self,
        func: Callable,
        retry_config: Optional[RetryConfig] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        retry_manager = RetryManager(retry_config)
        
        try:
            result, status = await retry_manager.retry_async(func, *args, **kwargs)
            
            if status != RetryResult.SUCCESS:
                # Log the final failure
                last_exception = kwargs.get('last_exception')
                if last_exception:
                    structured_error = create_error_from_exception(last_exception)
                    self.error_logger.log_error(structured_error)
                raise Exception(f"Retry failed with status: {status}")
            
            return result
            
        except Exception as e:
            structured_error = create_error_from_exception(e)
            self.error_logger.log_error(structured_error)
            raise
    
    def protect_with_circuit_breaker(
        self,
        service_name: str,
        func: Callable,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """Protect function with circuit breaker"""
        circuit_breaker = self.circuit_breaker_registry.get_or_create(service_name, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await circuit_breaker.call_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'service_name': self.service_name,
            'timestamp': asyncio.get_event_loop().time(),
            'health': self.health_manager.get_health_dashboard_data(),
            'degradation': self.degradation_manager.get_degradation_info(),
            'alerts': {
                'active': len(self.alert_manager.get_active_alerts()),
                'stats': self.alert_manager.get_alert_stats()
            },
            'circuit_breakers': self.circuit_breaker_registry.get_all_states(),
            'recent_errors': len(self.error_logger.get_recent_errors(limit=100)),
            'monitoring_active': self._monitoring_active
        }
    
    def get_dashboard_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get dashboard data"""
        return self.dashboard.get_dashboard_data(force_refresh)
    
    def generate_status_report(self, period_hours: int = 24) -> str:
        """Generate comprehensive status report"""
        return self.dashboard.generate_report(period_hours)


# Global system instance
global_error_system = ErrorHandlingSystem()


# Convenience decorators and functions
def with_error_handling(
    operation_name: str = "unknown",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Decorator for comprehensive error handling"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with global_error_system.error_context(
                operation_name, user_id, session_id
            ):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return await asyncio.to_thread(func, *args, **kwargs)
                except Exception as e:
                    structured_error = create_error_from_exception(e)
                    global_error_system.error_logger.log_error(structured_error)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                structured_error = create_error_from_exception(e)
                global_error_system.error_logger.log_error(structured_error)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def with_circuit_breaker(
    service_name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator for circuit breaker protection"""
    def decorator(func):
        return global_error_system.protect_with_circuit_breaker(service_name, func, config)
    return decorator


def with_retry(
    config: Optional[RetryConfig] = None
):
    """Decorator for retry logic"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await global_error_system.execute_with_retry(func, config, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, use sync retry
            retry_manager = RetryManager(config)
            result, status = retry_manager.retry_sync(func, *args, **kwargs)
            if status != RetryResult.SUCCESS:
                raise Exception(f"Retry failed with status: {status}")
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Example configuration
DEFAULT_CONFIG = {
    'health_checks': {
        'checks': [
            {
                'name': 'system_health',
                'type': 'resource',
                'config': {
                    'interval': 60,
                    'critical': True
                }
            }
        ]
    },
    'circuit_breakers': {
        'services': [
            {
                'name': 'external_api',
                'config': {
                    'failure_threshold': 5,
                    'timeout': 30.0
                }
            }
        ]
    },
    'alerts': {
        'rules': [
            {
                'name': 'high_error_rate',
                'condition': 'error_rate > 10',
                'severity': 'error',
                'description': 'Error rate exceeds 10 per minute',
                'notification_channels': ['console', 'log']
            }
        ]
    }
}


# Initialization function
async def initialize_error_system(
    service_name: str,
    config: Optional[Dict[str, Any]] = None
) -> ErrorHandlingSystem:
    """Initialize and return error handling system"""
    system = ErrorHandlingSystem(service_name, config or DEFAULT_CONFIG)
    await system.initialize()
    return system


# Example usage patterns
async def example_async_operation():
    """Example of using the error handling system in async code"""
    
    @with_error_handling(operation_name="user_data_fetch")
    @with_retry(API_RETRY_CONFIG)
    @with_circuit_breaker("user_service")
    async def fetch_user_data(user_id: str):
        # This function will be automatically protected
        # with error handling, retry logic, and circuit breaker
        # Simulate API call
        await asyncio.sleep(0.1)
        if user_id == "error":
            raise ConnectionError("User service unavailable")
        return {"id": user_id, "name": f"User {user_id}"}
    
    return await fetch_user_data("123")


def example_sync_operation():
    """Example of using the error handling system in sync code"""
    
    @with_error_handling(operation_name="data_processing")
    @with_retry(DATABASE_RETRY_CONFIG)
    @circuit_breaker("database_service", LENIENT_CIRCUIT_BREAKER_CONFIG)
    def process_data(data: list):
        # This function will be automatically protected
        import random
        if random.random() < 0.3:
            raise DatabaseError("Database connection failed")
        return [item.upper() for item in data]
    
    return process_data(["a", "b", "c"])


if __name__ == "__main__":
    # Example initialization and usage
    async def main():
        # Initialize the system
        system = await initialize_error_system("example_service")
        
        # Use the system
        result = await example_async_operation()
        print(f"Result: {result}")
        
        # Get system status
        status = await system.get_system_status()
        print(f"System status: {json.dumps(status, indent=2, default=str)}")
        
        # Generate report
        report = system.generate_status_report()
        print(f"Report:\n{report}")
    
    asyncio.run(main())