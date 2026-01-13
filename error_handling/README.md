# Error Handling and Retry Logic System

A comprehensive, production-ready error handling framework with intelligent retry mechanisms, circuit breaker patterns, fallback strategies, and automated recovery for Python applications.

## 🎯 Features

### Core Components

- **Structured Error Types** - Categorized, typed errors with context and correlation IDs
- **Intelligent Retry Mechanisms** - Exponential backoff with customizable policies
- **Circuit Breaker Patterns** - Service resilience with automatic failure detection
- **Fallback Strategies** - Multiple fallback options for degraded functionality
- **Error Logging & Tracing** - Comprehensive logging with correlation ID tracking
- **Health Checks** - Automated monitoring with recovery actions
- **Graceful Degradation** - Tiered service degradation based on system health
- **Error Dashboard** - Real-time monitoring and alerting system

### Advanced Features

- **Automatic Recovery** - Self-healing systems with configurable recovery actions
- **Distributed Tracing** - Request correlation across microservices
- **Performance Monitoring** - Real-time metrics and trend analysis
- **Alert Management** - Configurable alerts with multiple notification channels
- **Service Tiering** - Critical vs non-critical service prioritization

## 🚀 Quick Start

### Basic Setup

```python
import asyncio
from error_handling import initialize_error_system

async def main():
    # Initialize error handling system
    system = await initialize_error_system("my_service")
    
    # Use with decorators for automatic protection
    from error_handling import with_error_handling, with_retry, with_circuit_breaker
    
    @with_error_handling(operation_name="user_lookup")
    @with_retry()
    @with_circuit_breaker("user_service")
    async def get_user(user_id: str):
        # Your business logic here
        return {"id": user_id, "name": f"User {user_id}"}
    
    # Use the protected function
    user = await get_user("123")
    print(user)

asyncio.run(main())
```

### Error Context and Correlation

```python
from error_handling import error_context

async def process_request(user_id: str):
    # Create correlation context for tracing
    async with error_context(
        operation_name="user_processing",
        user_id=user_id,
        session_id="session_123"
    ):
        # All errors in this context will be correlated
        result = await some_risky_operation()
        return result
```

### Retry Configuration

```python
from error_handling import RetryConfig, with_retry

# Custom retry configuration
custom_config = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=[ConnectionError, TimeoutError]
)

@with_retry(config=custom_config)
async def api_call():
    # Will retry on ConnectionError and TimeoutError
    # with exponential backoff and jitter
    return await external_api.request()
```

### Circuit Breaker Protection

```python
from error_handling import circuit_breaker, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,
    timeout=60.0,
    success_threshold=3,
    failure_mode="count_based"
)

@circuit_breaker("external_service", config)
async def call_external_api():
    # Protected by circuit breaker
    # Automatically opens after 5 failures
    # Half-opens after timeout to test recovery
    return await external_api.call()
```

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Error Handling System                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Error Types │  │ Retry Engine │  │ Circuit Breakers   │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Fallback    │  │ Health Checks│  │ Graceful Degradation│ │
│  │ Strategies  │  │ & Recovery   │  │                     │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Error       │  │ Correlation  │  │ Error Dashboard     │ │
│  │ Logging     │  │ Tracing      │  │ & Alerts            │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Error Flow

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────────┐    ┌─────────────┐    ┌─────────────────┐
│ Correlation ID  │───▶│ Try Primary │───▶│ Success?        │
│ Generation      │    │ Service     │    │                 │
└─────────────────┘    └──────┬──────┘    └──────┬──────────┘
                              │                     │
                              ▼                     ▼
                       ┌─────────────┐    ┌─────────────────┐
                       │ Retry Logic │    │ Return Response │
                       │ (if needed) │    │                 │
                       └──────┬──────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────┐    ┌─────────────────┐
                       │ Circuit     │───▶│ Use Fallback    │
                       │ Breaker     │    │ (if available)  │
                       └──────┬──────┘    └──────┬──────────┘
                              │                     │
                              ▼                     ▼
                       ┌─────────────┐    ┌─────────────────┐
                       │ Log Error & │    │ Log Success &   │
                       │ Trigger     │    │ Update Metrics  │
                       │ Recovery    │    │                 │
                       └─────────────┘    └─────────────────┘
```

## 📊 Error Types

### Structured Error Hierarchy

```python
from error_handling import (
    NetworkError, DatabaseError, APIError, ValidationError,
    TimeoutError, RateLimitError, SystemError,
    ErrorCategory, ErrorSeverity
)

# Network-related errors
try:
    await network_call()
except ConnectionError as e:
    raise NetworkError("Connection failed", original_error=e)

# Database errors
try:
    await db_query()
except Exception as e:
    raise DatabaseError("Query failed", original_error=e)

# API errors with automatic status code handling
try:
    response = await api_call()
except HTTPError as e:
    raise APIError(f"API call failed: {e}", status_code=e.response.status_code)
```

### Error Context

```python
from error_handling import LogContext

context = LogContext(
    correlation_id="req-123",
    service_name="user_service",
    operation_name="get_user",
    user_id="user-456",
    metadata={"request_size": 1024}
)

error = NetworkError("Connection failed", context=context)
```

## 🔄 Retry Mechanisms

### Built-in Configurations

```python
from error_handling import (
    NETWORK_RETRY_CONFIG, DATABASE_RETRY_CONFIG, API_RETRY_CONFIG
)

@with_retry(NETWORK_RETRY_CONFIG)
async def network_operation():
    # Automatically retries with network-optimized settings
    pass

@with_retry(DATABASE_RETRY_CONFIG)
async def db_operation():
    # Database-specific retry logic
    pass
```

### Custom Retry Policies

```python
from error_handling import RetryConfig, with_retry

# Aggressive retry for critical operations
critical_config = RetryConfig(
    max_attempts=10,
    base_delay=0.5,
    max_delay=60.0,
    exponential_base=1.5,
    retryable_exceptions=[ConnectionError, TimeoutError]
)

@with_retry(critical_config)
async def critical_operation():
    # Highly resilient operation
    pass
```

### Retry with Custom Logic

```python
from error_handling import RetryManager

async def custom_retry_example():
    manager = RetryManager(RetryConfig(max_attempts=3))
    
    async def risky_operation():
        if random.random() < 0.5:
            raise ConnectionError("Temporary failure")
        return "Success!"
    
    result, status = await manager.retry_async(risky_operation)
    
    if status == RetryResult.SUCCESS:
        print(f"Operation succeeded: {result}")
    else:
        print(f"Operation failed after retries")
```

## ⚡ Circuit Breaker Patterns

### Basic Circuit Breaker

```python
@circuit_breaker("payment_service")
async def process_payment(amount: float):
    # Automatically protected by circuit breaker
    # Opens after failure threshold, half-opens to test recovery
    return await payment_gateway.charge(amount)
```

### Advanced Configuration

```python
from error_handling import CircuitBreakerConfig, FailureMode

# Strict circuit breaker
strict_config = CircuitBreakerConfig(
    failure_threshold=3,
    timeout=30.0,
    success_threshold=2,
    failure_mode=FailureMode.COUNT_BASED
)

# Lenient circuit breaker with percentage-based failure detection
lenient_config = CircuitBreakerConfig(
    failure_threshold=10,
    timeout=120.0,
    success_threshold=5,
    failure_mode=FailureMode.PERCENTAGE_BASED,
    window_size=50,
    failure_percentage_threshold=80.0
)
```

### Circuit Breaker with Fallback

```python
from error_handling import CircuitBreakerWithFallback

class PaymentService:
    def __init__(self):
        self.circuit_breaker = CircuitBreaker("payment_service")
        self.fallback_manager = FallbackManager()
    
    async def charge_with_fallback(self, amount: float):
        # Use integrated circuit breaker with fallback
        cb_with_fallback = CircuitBreakerWithFallback(
            self.circuit_breaker,
            self.fallback_manager
        )
        
        result = await cb_with_fallback.call_with_fallback(
            self._charge_primary,
            ["fallback_to_queue", "default_response"],
            amount=amount
        )
        return result
```

## 🔄 Fallback Strategies

### Fallback Types

```python
# Cache fallback
from error_handling import CacheFallback, FallbackManager

cache_fallback = CacheFallback(get_cache, ttl=300)
fallback_manager.register("cache", cache_fallback.get)

# Static data fallback
static_data = {"default_user": {"id": "0", "name": "Default User"}}
static_fallback = StaticDataFallback(static_data)
fallback_manager.register("static", static_fallback.get)

# Remote service fallback
async def backup_service_call(*args, **kwargs):
    return await backup_api.request(*args, **kwargs)

remote_fallback = RemoteFallback(backup_service_call, timeout=10.0)
fallback_manager.register("remote", remote_fallback.call)
```

### Cascade Fallback Pattern

```python
@with_fallback(fallback_names=["cache", "static", "remote", "default"])
async def get_user_data(user_id: str):
    # Primary data source
    return await primary_api.get_user(user_id)

# If primary fails, tries cache, then static data, then remote service, then default
user_data = await get_user_data("123")
```

## 🏥 Health Checks

### HTTP Health Check

```python
from error_handling import HTTPHealthChecker, HealthCheckConfig

http_checker = HTTPHealthChecker(
    name="api_health",
    url="https://api.example.com/health",
    config=HealthCheckConfig(
        interval=30,
        failure_threshold=3,
        critical=True
    )
)

system.health_manager.add_checker(http_checker)
```

### Database Health Check

```python
async def get_db_connection():
    # Your database connection logic
    return await connect_to_database()

db_checker = DatabaseHealthChecker(
    name="database_health",
    connection_func=get_db_connection,
    query="SELECT 1",
    config=HealthCheckConfig(interval=60, critical=True)
)

system.health_manager.add_checker(db_checker)
```

### Custom Health Check

```python
async def custom_service_check():
    # Your custom health check logic
    return await check_service_status()

custom_checker = CustomHealthChecker(
    name="custom_service",
    check_func=custom_service_check,
    config=HealthCheckConfig(interval=30)
)

system.health_manager.add_checker(custom_checker)
```

### Resource Health Check

```python
from error_handling import ResourceHealthChecker

resource_checker = ResourceHealthChecker(
    name="system_resources",
    memory_threshold=0.85,  # 85% memory usage
    disk_threshold=0.90,    # 90% disk usage
    cpu_threshold=0.80      # 80% CPU usage
)

system.health_manager.add_checker(resource_checker)
```

### Recovery Actions

```python
from error_handling import restart_service_action, clear_cache_action

# Add recovery actions
checker.add_recovery_action(restart_service_action("problematic_service"))
checker.add_recovery_action(clear_cache_action("user_cache"))

# Custom recovery action
async def custom_recovery_action(checker):
    await restart_database_connections()
    await clear_application_cache()

checker.add_recovery_action(custom_recovery_action)
```

## 📈 Graceful Degradation

### Service Tiering

```python
from error_handling import (
    ServiceInfo, ServiceTier, graceful_degradation,
    DegradationLevel
)

# Register services with different tiers
service_registry = GracefulDegradationManager()

service_registry.register_service(ServiceInfo(
    name="payment_service",
    tier=ServiceTier.CRITICAL,
    description="Payment processing - must always be available"
))

service_registry.register_service(ServiceInfo(
    name="user_profile",
    tier=ServiceTier.IMPORTANT,
    description="User profile management"
))

service_registry.register_service(ServiceInfo(
    name="analytics_service",
    tier=ServiceTier.LUXURY,
    description="Analytics and reporting - can be disabled"
))
```

### Degradation Rules

```python
from error_handling import DegradationRule

# Rule to disable non-critical services when error rate is high
high_error_rule = DegradationRule(
    trigger_condition="error_rate > 10",
    target_level=DegradationLevel.LIMITED_FEATURES,
    services_to_disable=["analytics_service"],
    timeout_minutes=15
)

# Rule for emergency mode
emergency_rule = DegradationRule(
    trigger_condition="health_status == 'unhealthy'",
    target_level=DegradationLevel.EMERGENCY_MODE,
    capacity_reduction=0.5,
    timeout_minutes=30
)

service_registry.add_degradation_rule(high_error_rule)
service_registry.add_degradation_rule(emergency_rule)
```

### Protected Services

```python
@graceful_degradation(
    service_name="payment_service",
    tier=ServiceTier.CRITICAL,
    fallback=lambda: {"status": "queued", "message": "Payment queued for processing"}
)
async def process_payment(amount: float):
    # This service will be protected by graceful degradation
    # Falls back to queuing if the service is degraded
    return await payment_gateway.charge(amount)

@graceful_degradation(
    service_name="analytics_service",
    tier=ServiceTier.LUXURY,
    fallback=lambda: {"data": "cached_analytics", "source": "cache"}
)
async def generate_analytics():
    # This service can be completely disabled during degradation
    return await analytics_engine.generate_report()
```

## 📊 Error Dashboard & Monitoring

### Dashboard Configuration

```python
from error_handling import dashboard_context

async def main():
    async with dashboard_context() as dashboard:
        # System is now monitored with alerts
        
        # Your application code here
        await run_application()
        
        # Access dashboard data
        data = dashboard.get_dashboard_data()
        print(f"Active alerts: {data['alerts']['total_active']}")
        print(f"Error rate: {data['errors']['error_rate']}")
```

### Alert Rules

```python
from error_handling import AlertRule, AlertSeverity

# High error rate alert
error_rate_rule = AlertRule(
    name="high_error_rate",
    condition="error_rate > 10",
    severity=AlertSeverity.ERROR,
    description="Error rate exceeds 10 errors per minute",
    notification_channels=["console", "log"]
)

# Critical health alert
health_rule = AlertRule(
    name="system_unhealthy",
    condition="health_status == 'unhealthy'",
    severity=AlertSeverity.CRITICAL,
    description="System health is critical",
    notification_channels=["console", "log"],
    cooldown_period=600  # 10 minutes
)

system.alert_manager.add_alert_rule(error_rate_rule)
system.alert_manager.add_alert_rule(health_rule)
```

### Custom Notification Channels

```python
async def slack_notification(alert, rule):
    # Send alert to Slack
    await slack_client.send_message(
        channel="#alerts",
        text=f"🚨 {alert.severity.value.upper()}: {alert.title}\n{alert.message}"
    )

system.alert_manager.register_channel("slack", slack_notification)

# Add rule with custom channel
slack_rule = AlertRule(
    name="payment_failures",
    condition="errors_by_category.get('database', 0) > 5",
    severity=AlertSeverity.CRITICAL,
    description="Multiple database errors detected",
    notification_channels=["slack", "log"]
)
```

## 🔍 Error Logging & Tracing

### Structured Logging

```python
from error_handling import with_logging, LogContext

@with_logging()
async def user_operation(user_id: str):
    # Automatically logged with correlation ID
    return await user_service.get_user(user_id)
```

### Manual Logging

```python
from error_handling import global_error_logger, create_error_from_exception

try:
    result = await risky_operation()
except Exception as e:
    # Create structured error with context
    error = create_error_from_exception(
        e,
        context=LogContext(
            service_name="user_service",
            operation_name="get_user",
            user_id="123"
        )
    )
    
    # Log with full context
    global_error_logger.log_error(error)
    raise
```

### Correlation ID Tracking

```python
from error_handling import extract_correlation_id, inject_correlation_id, error_context

async def handle_request(request):
    # Extract correlation ID from headers
    correlation_id = extract_correlation_id(request.headers)
    
    # Create context for this request
    async with error_context(
        operation_name="handle_request",
        correlation_id=correlation_id,
        user_id=request.user_id
    ):
        # All operations in this context will share correlation ID
        result = await process_request(request)
        
        # Inject correlation ID in response headers
        response_headers = inject_correlation_id({}, correlation_id)
        return result, response_headers
```

## 🏗️ Complete Integration

### Full Configuration Example

```python
import asyncio
from error_handling import initialize_error_system

async def setup_production_service():
    """Complete production service setup"""
    
    config = {
        'health_checks': {
            'checks': [
                {
                    'name': 'database_health',
                    'type': 'database',
                    'config': {
                        'interval': 30,
                        'critical': True,
                        'failure_threshold': 3
                    }
                },
                {
                    'name': 'external_api',
                    'type': 'http',
                    'url': 'https://api.partner.com/health',
                    'config': {
                        'interval': 60,
                        'critical': False
                    }
                },
                {
                    'name': 'system_resources',
                    'type': 'resource',
                    'config': {
                        'interval': 120,
                        'critical': True
                    }
                }
            ]
        },
        'circuit_breakers': {
            'services': [
                {
                    'name': 'payment_gateway',
                    'config': {
                        'failure_threshold': 5,
                        'timeout': 30.0,
                        'success_threshold': 2
                    }
                },
                {
                    'name': 'email_service',
                    'config': {
                        'failure_threshold': 10,
                        'timeout': 60.0,
                        'success_threshold': 3
                    }
                }
            ]
        },
        'degradation': {
            'services': [
                {
                    'name': 'core_payment',
                    'tier': 'critical',
                    'description': 'Core payment processing'
                },
                {
                    'name': 'user_profile',
                    'tier': 'important',
                    'description': 'User profile management'
                },
                {
                    'name': 'recommendation_engine',
                    'tier': 'luxury',
                    'description': 'Personalization features'
                }
            ],
            'rules': [
                {
                    'condition': 'error_rate > 5',
                    'target_level': 'limited_features',
                    'services_to_disable': ['recommendation_engine'],
                    'timeout_minutes': 15
                },
                {
                    'condition': 'overall_health_status == "unhealthy"',
                    'target_level': 'essential_only',
                    'capacity_reduction': 0.5,
                    'timeout_minutes': 30
                }
            ]
        },
        'alerts': {
            'rules': [
                {
                    'name': 'high_error_rate',
                    'condition': 'error_rate > 10',
                    'severity': 'error',
                    'description': 'High error rate detected',
                    'notification_channels': ['console', 'log']
                },
                {
                    'name': 'service_critical',
                    'condition': 'errors_by_severity.get("critical", 0) > 0',
                    'severity': 'critical',
                    'description': 'Critical errors detected',
                    'notification_channels': ['console', 'log']
                }
            ]
        }
    }
    
    # Initialize the system
    system = await initialize_error_system("production_service", config)
    
    return system

# Use in production
async def production_main():
    system = await setup_production_service()
    
    @with_error_handling(operation_name="process_payment")
    @with_retry(DATABASE_RETRY_CONFIG)
    @with_circuit_breaker("payment_gateway")
    async def process_payment(amount: float, user_id: str):
        return await payment_service.charge(amount, user_id)
    
    # Your application logic here
    while True:
        try:
            # Process payments or other business logic
            payment_result = await process_payment(100.0, "user123")
            print(f"Payment processed: {payment_result}")
        except Exception as e:
            print(f"Payment failed: {e}")
        
        await asyncio.sleep(1)
```

## 📈 Monitoring & Metrics

### Get System Status

```python
async def monitor_system():
    system = await initialize_error_system("monitored_service")
    
    while True:
        status = await system.get_system_status()
        
        print(f"Health: {status['health']['overall_status']}")
        print(f"Active alerts: {status['alerts']['active']}")
        print(f"Degradation level: {status['degradation']['current_level']}")
        print(f"Error count: {status['recent_errors']}")
        
        await asyncio.sleep(60)  # Check every minute
```

### Generate Reports

```python
# Generate comprehensive report
report = system.generate_status_report(period_hours=24)
print(report)

# Export dashboard data
dashboard_data = system.get_dashboard_data()
json_export = system.dashboard.export_data(format='json')
```

## 🛠️ Best Practices

### 1. Use Appropriate Retry Configurations

```python
# For network operations
@with_retry(NETWORK_RETRY_CONFIG)
async def network_call():
    pass

# For database operations
@with_retry(DATABASE_RETRY_CONFIG)
async def db_call():
    pass

# For API calls
@with_retry(API_RETRY_CONFIG)
async def api_call():
    pass
```

### 2. Configure Circuit Breakers Appropriately

```python
# Critical services need stricter thresholds
@circuit_breaker("payment_service", STRICT_CIRCUIT_BREAKER_CONFIG)
async def critical_operation():
    pass

# Less critical services can be more lenient
@circuit_breaker("analytics_service", LENIENT_CIRCUIT_BREAKER_CONFIG)
async def non_critical_operation():
    pass
```

### 3. Implement Meaningful Fallbacks

```python
@graceful_degradation(
    service_name="user_recommendations",
    tier=ServiceTier.LUXURY,
    fallback=lambda: {"recommendations": [], "source": "cache"}
)
async def get_recommendations(user_id: str):
    # Primary recommendation logic
    return await ml_service.get_recommendations(user_id)
```

### 4. Set Up Health Checks for Dependencies

```python
# Check external dependencies
external_api_check = HTTPHealthChecker(
    name="partner_api",
    url="https://partner-api.com/health"
)
system.health_manager.add_checker(external_api_check)

# Add recovery actions
external_api_check.add_recovery_action(
    restart_service_action("partner_api_connector")
)
```

### 5. Configure Alerts Appropriately

```python
# Don't alert on every error - use rate-based alerts
rate_based_alert = AlertRule(
    name="high_error_rate",
    condition="error_rate > 5",
    severity=AlertSeverity.WARNING,
    description="Error rate above threshold"
)

# Critical alerts for actual problems
critical_alert = AlertRule(
    name="service_down",
    condition="overall_health_status == 'unhealthy'",
    severity=AlertSeverity.CRITICAL,
    description="Service is unhealthy"
)
```

## 🧪 Testing

### Unit Testing with Error Handling

```python
import pytest
from unittest.mock import AsyncMock, patch
from error_handling import with_retry, NETWORK_RETRY_CONFIG

@pytest.mark.asyncio
async def test_with_retry():
    call_count = 0
    
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "Success"
    
    @with_retry(RetryConfig(max_attempts=5))
    async def protected_function():
        return await flaky_function()
    
    result = await protected_function()
    assert result == "Success"
    assert call_count == 3  # Should have retried twice
```

### Testing Circuit Breaker Behavior

```python
@pytest.mark.asyncio
async def test_circuit_breaker():
    from error_handling import CircuitBreaker, CircuitBreakerConfig
    
    cb = CircuitBreaker("test_service", CircuitBreakerConfig(failure_threshold=2))
    
    # Test failure threshold
    for _ in range(2):
        try:
            await cb.call_async(lambda: 1/0)
        except:
            pass
    
    # Circuit should be open now
    try:
        await cb.call_async(lambda: "success")
        assert False, "Should have raised CircuitBreakerOpenError"
    except Exception as e:
        assert "Circuit breaker" in str(e)
```

## 🚨 Troubleshooting

### Common Issues

1. **High retry rates**
   - Check if retryable exceptions are properly configured
   - Verify base delay and max delay settings
   - Consider if the operation should retry at all

2. **Circuit breaker opens too quickly**
   - Increase failure threshold
   - Check if errors are transient vs permanent
   - Consider different failure mode (percentage vs count)

3. **Degradation not triggering**
   - Verify degradation rules are properly configured
   - Check metrics collection is working
   - Ensure degradation monitoring is running

4. **Missing correlation IDs**
   - Check error context is properly set
   - Verify correlation ID extraction/injection
   - Ensure context propagation in async calls

### Debug Mode

```python
import logging

# Enable debug logging for error handling
logging.getLogger("error_handling").setLevel(logging.DEBUG)
logging.getLogger("circuit_breaker").setLevel(logging.DEBUG)
logging.getLogger("graceful_degradation").setLevel(logging.DEBUG)
```

## 📚 API Reference

### Decorators

- `@with_error_handling(operation_name, user_id, session_id)` - Add comprehensive error handling
- `@with_retry(config)` - Add retry logic with exponential backoff
- `@with_circuit_breaker(service_name, config)` - Protect with circuit breaker
- `@graceful_degradation(service_name, tier, fallback)` - Add graceful degradation
- `@with_fallback(fallback_manager, fallback_names)` - Add fallback strategies
- `@with_logging(error_logger, tracing_logger)` - Add structured logging
- `@health_checkable(check_type, name, config)` - Make function health-checkable

### Classes

- `ErrorHandlingSystem` - Main system class
- `StructuredError` - Base error class
- `RetryManager` - Retry logic manager
- `CircuitBreaker` - Circuit breaker implementation
- `GracefulDegradationManager` - Service degradation manager
- `HealthCheckManager` - Health monitoring manager
- `AlertManager` - Alert and notification manager
- `ErrorDashboard` - Dashboard and reporting

### Configuration Classes

- `RetryConfig` - Retry configuration
- `CircuitBreakerConfig` - Circuit breaker configuration
- `HealthCheckConfig` - Health check configuration
- `FallbackConfig` - Fallback configuration
- `AlertRule` - Alert rule configuration

## 🤝 Contributing

This error handling system is designed to be extensible. To add new features:

1. Follow the existing patterns for configuration and error handling
2. Add comprehensive tests
3. Update documentation
4. Ensure backward compatibility

## 📄 License

This error handling system is provided as-is for production use in Python applications.

---

**Built for production environments with enterprise-grade reliability and monitoring capabilities.**