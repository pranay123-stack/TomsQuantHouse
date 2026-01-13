"""
Test Suite for Error Handling System

This file contains comprehensive tests for all components of the error handling system.
Run with: pytest error_handling/test_suite.py -v
"""
import asyncio
import pytest
import time
import random
from unittest.mock import AsyncMock, patch, MagicMock

# Import all components to test
from error_handling import (
    initialize_error_system,
    with_error_handling, with_retry, with_circuit_breaker, graceful_degradation,
    ErrorHandlingSystem, NetworkError, DatabaseError, APIError,
    RetryConfig, RetryManager, RetryResult,
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    GracefulDegradationManager, DegradationLevel, ServiceTier, ServiceInfo,
    HealthCheckManager, HealthStatus, HTTPHealthChecker, CustomHealthChecker,
    AlertRule, AlertSeverity, AlertManager, default_metric_store,
    ErrorLogger, LogContext, ErrorContext, global_error_logger
)


class TestErrorTypes:
    """Test structured error types"""
    
    def test_network_error_creation(self):
        """Test NetworkError creation"""
        error = NetworkError("Connection failed")
        assert error.category.value == "network"
        assert error.severity.value == "medium"
        assert error.retry_policy.value == "exponential_backoff"
        assert "Connection failed" in str(error)
    
    def test_database_error_creation(self):
        """Test DatabaseError creation"""
        error = DatabaseError("Query failed")
        assert error.category.value == "database"
        assert error.severity.value == "high"
        assert error.retry_policy.value == "exponential_backoff"
    
    def test_api_error_with_status_code(self):
        """Test APIError with different status codes"""
        error_500 = APIError("Server error", status_code=500)
        assert error_500.severity.value == "high"
        assert error_500.retry_policy.value == "exponential_backoff"
        
        error_404 = APIError("Not found", status_code=404)
        assert error_404.severity.value == "medium"
        assert error_404.retry_policy.value == "no_retry"
    
    def test_error_context_tracking(self):
        """Test error context with correlation ID"""
        context = LogContext(
            service_name="test_service",
            operation_name="test_operation",
            user_id="user123"
        )
        
        error = NetworkError("Test error", context=context)
        assert error.context.service_name == "test_service"
        assert error.context.operation_name == "test_operation"
        assert error.context.user_id == "user123"
        assert error.context.correlation_id is not None


class TestRetryMechanism:
    """Test retry logic and exponential backoff"""
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful retry after initial failures"""
        retry_manager = RetryManager(RetryConfig(max_attempts=5))
        
        call_count = 0
        
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "Success"
        
        result, status = await retry_manager.retry_async(flaky_function)
        
        assert result == "Success"
        assert status == RetryResult.SUCCESS
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test retry exhaustion"""
        retry_manager = RetryManager(RetryConfig(max_attempts=3))
        
        async def always_failing_function():
            raise ConnectionError("Always fails")
        
        result, status = await retry_manager.retry_async(always_failing_function)
        
        assert result is None
        assert status == RetryResult.MAX_RETRIES_EXCEEDED
    
    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Test no retry on non-retryable exceptions"""
        retry_manager = RetryManager(RetryConfig(max_attempts=5))
        
        call_count = 0
        
        async def validation_error_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Validation failed")
        
        result, status = await retry_manager.retry_async(validation_error_function)
        
        assert result is None
        assert status == RetryResult.FAILURE
        assert call_count == 1  # Should not retry
    
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation"""
        retry_manager = RetryManager(RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        ))
        
        # Test delay calculation for different attempts
        delay_1 = retry_manager.calculate_delay(1, ConnectionError())
        delay_2 = retry_manager.calculate_delay(2, ConnectionError())
        delay_3 = retry_manager.calculate_delay(3, ConnectionError())
        
        assert delay_1 == 1.0
        assert delay_2 == 2.0
        assert delay_3 == 4.0
    
    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test retry decorator functionality"""
        call_count = 0
        
        @with_retry(RetryConfig(max_attempts=3))
        async def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "Success"
        
        result = await decorated_function()
        assert result == "Success"
        assert call_count == 2


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opens after failure threshold"""
        cb = CircuitBreaker("test_service", CircuitBreakerConfig(failure_threshold=3))
        
        # Fail to reach threshold
        for _ in range(2):
            try:
                await cb.call_async(lambda: 1/0)
            except:
                pass
        
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Reach threshold - should open
        try:
            await cb.call_async(lambda: 1/0)
        except:
            pass
        
        assert cb.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """Test circuit breaker blocks requests when open"""
        cb = CircuitBreaker("test_service", CircuitBreakerConfig(
            failure_threshold=1,
            timeout=1.0
        ))
        
        # Force circuit to open
        try:
            await cb.call_async(lambda: 1/0)
        except:
            pass
        
        # Should raise CircuitBreakerOpenError
        from error_handling.circuit_breaker import CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call_async(lambda: "Should not reach here")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open recovery"""
        cb = CircuitBreaker("test_service", CircuitBreakerConfig(
            failure_threshold=2,
            timeout=0.1,  # Short timeout for testing
            success_threshold=2
        ))
        
        # Open circuit
        for _ in range(2):
            try:
                await cb.call_async(lambda: 1/0)
            except:
                pass
        
        assert cb.state == CircuitBreakerState.OPEN
        
        # Wait for timeout and transition to half-open
        await asyncio.sleep(0.2)
        assert cb.state == CircuitBreakerState.HALF_OPEN
        
        # First call in half-open should succeed to close circuit
        success_count = 0
        for _ in range(2):
            result = await cb.call_async(lambda: "Success")
            success_count += 1
        
        assert success_count == 2
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics tracking"""
        cb = CircuitBreaker("test_service")
        
        # Simulate some calls
        cb._record_call(success=True, duration=0.1)
        cb._record_call(success=False, duration=0.2)
        cb._record_call(success=True, duration=0.15)
        
        info = cb.get_state()
        
        assert info['metrics']['total_calls'] == 3
        assert info['metrics']['successful_calls'] == 2
        assert info['metrics']['failed_calls'] == 1
        assert info['metrics']['success_rate'] == pytest.approx(66.67, rel=1e-2)


class TestGracefulDegradation:
    """Test graceful degradation system"""
    
    @pytest.mark.asyncio
    async def test_degradation_rule_triggering(self):
        """Test degradation rule triggering"""
        manager = GracefulDegradationManager()
        
        # Add degradation rule
        rule = DegradationRule(
            trigger_condition="error_rate > 5",
            target_level=DegradationLevel.LIMITED_FEATURES,
            services_to_disable=["analytics"],
            timeout_minutes=10
        )
        manager.add_degradation_rule(rule)
        
        # Test rule triggering
        metrics = {"error_rate": 10}
        target_level = await manager.evaluate_degradation(metrics)
        
        assert target_level == DegradationLevel.LIMITED_FEATURES
    
    @pytest.mark.asyncio
    async def test_service_tiering(self):
        """Test service tiering with degradation"""
        manager = GracefulDegradationManager()
        
        # Register services
        manager.register_service(ServiceInfo(
            name="payment",
            tier=ServiceTier.CRITICAL
        ))
        manager.register_service(ServiceInfo(
            name="analytics",
            tier=ServiceTier.LUXURY
        ))
        
        # Apply degradation
        await manager.apply_degradation(DegradationLevel.LIMITED_FEATURES, "Test degradation")
        
        # Check service states
        assert manager.get_service_status("payment") == True  # Critical service
        assert manager.get_service_status("analytics") == False  # Luxury service
    
    def test_feature_flags(self):
        """Test feature flags with degradation"""
        from error_handling.graceful_degradation import FeatureFlags
        
        manager = GracefulDegradationManager()
        feature_flags = FeatureFlags(manager)
        
        # Register features
        feature_flags.register_feature("premium_analytics", ServiceTier.LUXURY)
        feature_flags.register_feature("basic_features", ServiceTier.IMPORTANT)
        
        # Test feature flag behavior
        assert feature_flags.is_feature_enabled("premium_analytics") == True
        assert feature_flags.is_feature_enabled("basic_features") == True
        
        # Apply degradation
        manager.current_level = DegradationLevel.ESSENTIAL_ONLY
        
        # Luxury features should be disabled
        assert feature_flags.is_feature_enabled("premium_analytics") == False
        assert feature_flags.is_feature_enabled("basic_features") == True


class TestHealthChecks:
    """Test health check system"""
    
    @pytest.mark.asyncio
    async def test_custom_health_check(self):
        """Test custom health check"""
        call_count = 0
        
        async def custom_check():
            nonlocal call_count
            call_count += 1
            return call_count < 2  # Fail first time, succeed second
        
        checker = CustomHealthChecker(
            name="test_check",
            check_func=custom_check,
            config=HealthCheckConfig(failure_threshold=2)
        )
        
        # First check - should fail
        result1 = await checker.check()
        assert result1.status == HealthStatus.UNHEALTHY
        assert result1.is_unhealthy
        
        # Second check - should succeed
        result2 = await checker.check()
        assert result2.status == HealthStatus.HEALTHY
        assert result2.is_healthy
    
    @pytest.mark.asyncio
    async def test_health_check_recovery(self):
        """Test health check recovery"""
        checker = CustomHealthChecker(
            name="recovery_check",
            check_func=lambda: False,  # Always fails initially
            config=HealthCheckConfig(
                failure_threshold=2,
                recovery_threshold=1
            )
        )
        
        # Fail multiple times
        await checker.check()  # Fail count: 1
        await checker.check()  # Fail count: 2 (unhealthy)
        
        assert checker.get_status() == HealthStatus.UNHEALTHY
        
        # Change check to succeed
        async def succeed_check():
            return True
        checker.check_func = succeed_check
        
        await checker.check()  # Success count: 1 (should recover)
        assert checker.get_status() == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_health_check_manager(self):
        """Test health check manager"""
        manager = HealthCheckManager()
        
        # Add checker
        checker = CustomHealthChecker(
            name="test_checker",
            check_func=lambda: True,
            config=HealthCheckConfig(interval=10)
        )
        manager.add_checker(checker)
        
        # Run checks
        results = await manager.check_all()
        
        assert "test_checker" in results
        assert results["test_checker"].status == HealthStatus.HEALTHY
        assert manager.get_overall_status() == HealthStatus.HEALTHY


class TestAlertManager:
    """Test alert and monitoring system"""
    
    @pytest.mark.asyncio
    async def test_alert_rule_triggering(self):
        """Test alert rule triggering"""
        alert_manager = AlertManager()
        
        # Add alert rule
        rule = AlertRule(
            name="high_error_rate",
            condition="error_rate > 5",
            severity=AlertSeverity.ERROR,
            description="High error rate detected"
        )
        alert_manager.add_alert_rule(rule)
        
        # Trigger metrics that should activate alert
        metrics = {"error_rate": 10}
        
        await alert_manager._evaluate_rule(rule, metrics)
        
        # Check if alert was created
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) > 0
        
        high_error_alerts = [
            alert for alert in active_alerts
            if alert.rule_name == "high_error_rate"
        ]
        assert len(high_error_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_alert_cooldown(self):
        """Test alert cooldown period"""
        alert_manager = AlertManager()
        
        rule = AlertRule(
            name="test_alert",
            condition="error_rate > 5",
            severity=AlertSeverity.WARNING,
            description="Test alert",
            cooldown_period=1  # 1 second cooldown
        )
        alert_manager.add_alert_rule(rule)
        
        # Trigger alert
        metrics = {"error_rate": 10}
        await alert_manager._evaluate_rule(rule, metrics)
        
        assert len(alert_manager.get_active_alerts()) == 1
        
        # Trigger again immediately (should not create new alert)
        await alert_manager._evaluate_rule(rule, metrics)
        assert len(alert_manager.get_active_alerts()) == 1
        
        # Wait for cooldown period
        await asyncio.sleep(1.1)
        
        # Alert should resolve
        active_alerts = alert_manager.get_active_alerts()
        test_alerts = [a for a in active_alerts if a.rule_name == "test_alert"]
        assert len(test_alerts) == 0


class TestErrorLogging:
    """Test error logging and correlation tracking"""
    
    @pytest.mark.asyncio
    async def test_structured_error_logging(self):
        """Test structured error logging"""
        logger = ErrorLogger()
        
        error = NetworkError("Test network error")
        logger.log_error(error)
        
        recent_errors = logger.get_recent_errors()
        assert len(recent_errors) > 0
        
        logged_error = recent_errors[-1]
        assert 'error' in logged_error
        assert logged_error['error']['category'] == 'network'
        assert logged_error['error']['severity'] == 'medium'
    
    @pytest.mark.asyncio
    async def test_correlation_context(self):
        """Test correlation context tracking"""
        from error_handling.error_logging import correlation_context
        
        context = LogContext(
            service_name="test_service",
            operation_name="test_operation",
            user_id="user123"
        )
        
        async with correlation_context.context(context):
            current_context = correlation_context.get_current_context()
            assert current_context.service_name == "test_service"
            assert current_context.operation_name == "test_operation"
            assert current_context.user_id == "user123"
    
    def test_error_statistics(self):
        """Test error statistics"""
        logger = ErrorLogger()
        
        # Add some test errors
        for i in range(5):
            error = NetworkError(f"Error {i}")
            logger.log_error(error)
        
        stats = logger.get_error_stats()
        assert stats['total_errors'] == 5
        assert 'network' in stats['categories']


class TestErrorHandlingSystem:
    """Test complete error handling system integration"""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self):
        """Test system initialization"""
        system = ErrorHandlingSystem("test_service")
        assert system.service_name == "test_service"
        assert not system._initialized
        
        await system.initialize()
        assert system._initialized
        assert system._monitoring_active
    
    @pytest.mark.asyncio
    async def test_system_with_health_checks(self):
        """Test system with health checks"""
        config = {
            'health_checks': {
                'checks': [
                    {
                        'name': 'test_check',
                        'type': 'custom',
                        'config': {'interval': 10, 'critical': True}
                    }
                ]
            }
        }
        
        system = ErrorHandlingSystem("test_service", config)
        await system.initialize()
        
        # Check if health manager has the checker
        assert 'test_check' in system.health_manager.checkers
        assert system.health_manager.checkers['test_check'].config.critical
    
    @pytest.mark.asyncio
    async def test_decorator_integration(self):
        """Test decorator integration with error handling"""
        system = ErrorHandlingSystem("test_service")
        await system.initialize()
        
        call_count = 0
        
        @with_error_handling(operation_name="test_operation")
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "Success"
        
        result = await test_function()
        assert result == "Success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration"""
        system = ErrorHandlingSystem("test_service")
        await system.initialize()
        
        @with_circuit_breaker("test_service")
        async def failing_function():
            raise ConnectionError("Always fails")
        
        # Should eventually open circuit breaker
        for _ in range(5):
            try:
                await failing_function()
            except:
                pass
        
        # Check circuit breaker state
        cb_registry = system.circuit_breaker_registry
        assert 'test_service' in cb_registry._circuit_breakers
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_integration(self):
        """Test graceful degradation integration"""
        system = ErrorHandlingSystem("test_service")
        await system.initialize()
        
        @graceful_degradation(
            service_name="test_service",
            tier=ServiceTier.CRITICAL
        )
        async def critical_service():
            return "Critical service response"
        
        # Service should work normally
        result = await critical_service()
        assert result == "Critical service response"
        
        # Apply degradation
        await system.degradation_manager.apply_degradation(
            DegradationLevel.EMERGENCY_MODE,
            "Testing degradation"
        )
        
        # Critical services should still work
        result = await critical_service()
        assert result == "Critical service response"


# Performance and Load Tests
class TestPerformance:
    """Test system performance under load"""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test system performance with concurrent operations"""
        system = ErrorHandlingSystem("perf_test")
        await system.initialize()
        
        async def test_operation():
            await asyncio.sleep(0.01)  # Simulate work
            return "success"
        
        # Run many concurrent operations
        tasks = [test_operation() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
        assert all(r == "success" for r in results)
    
    @pytest.mark.asyncio
    async def test_retry_performance(self):
        """Test retry mechanism performance"""
        retry_manager = RetryManager(RetryConfig(max_attempts=3))
        
        async def slow_operation():
            await asyncio.sleep(0.01)  # Simulate network latency
            raise ConnectionError("Temporary failure")
        
        start_time = time.time()
        result, status = await retry_manager.retry_async(slow_operation)
        end_time = time.time()
        
        assert status == RetryResult.MAX_RETRIES_EXCEEDED
        assert end_time - start_time >= 0.06  # Should take at least 3 retries * 0.01s + delays
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_performance(self):
        """Test circuit breaker performance"""
        cb = CircuitBreaker("perf_test", CircuitBreakerConfig(failure_threshold=1000))
        
        start_time = time.time()
        
        # Test many rapid calls
        tasks = []
        for _ in range(100):
            task = cb.call_async(lambda: "success")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # All should succeed (no failures yet)
        assert all(r == "success" for r in results if not isinstance(r, Exception))
        assert end_time - start_time < 1.0  # Should be fast


# Integration Tests
class TestIntegration:
    """Test integration between components"""
    
    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker(self):
        """Test retry and circuit breaker working together"""
        cb = CircuitBreaker("integration_test", CircuitBreakerConfig(failure_threshold=2))
        retry_manager = RetryManager(RetryConfig(max_attempts=2))
        
        call_count = 0
        
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")
        
        # Use circuit breaker with retry
        protected_operation = cb.call_async
        result, status = await retry_manager.retry_async(protected_operation, flaky_operation)
        
        assert result is None
        assert status == RetryResult.MAX_RETRIES_EXCEEDED
        assert call_count == 2  # Should have retried twice
    
    @pytest.mark.asyncio
    async def test_health_checks_with_recovery(self):
        """Test health checks triggering recovery actions"""
        checker = CustomHealthChecker(
            name="integration_test",
            check_func=lambda: False,  # Always fails
            config=HealthCheckConfig(failure_threshold=1, critical=True)
        )
        
        recovery_called = False
        
        async def recovery_action(c):
            nonlocal recovery_called
            recovery_called = True
        
        checker.add_recovery_action(recovery_action)
        
        # Should trigger recovery
        await checker.check()
        
        assert checker.get_status() == HealthStatus.UNHEALTHY
        assert recovery_called  # Recovery action should have been called
    
    @pytest.mark.asyncio
    async def test_error_dashboard_data_collection(self):
        """Test error dashboard collects data correctly"""
        from error_handling.error_dashboard import ErrorDashboard
        
        dashboard = ErrorDashboard()
        
        # Generate some errors
        for i in range(5):
            error = NetworkError(f"Test error {i}")
            global_error_logger.log_error(error)
        
        # Get dashboard data
        data = dashboard.get_dashboard_data(force_refresh=True)
        
        assert 'errors' in data
        assert data['errors']['total_errors'] >= 5
        assert 'metrics' in data
        assert 'health' in data


# Main test execution
if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])