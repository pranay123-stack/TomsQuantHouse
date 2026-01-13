"""
Example Usage Patterns for the Error Handling System

This file demonstrates various ways to use the comprehensive error handling system
in real applications.
"""
import asyncio
import time
import random
from typing import Dict, List, Any

# Import the error handling system
from error_handling import (
    initialize_error_system,
    with_error_handling, with_retry, with_circuit_breaker, graceful_degradation,
    ErrorHandlingSystem, DegradationLevel, ServiceTier,
    NETWORK_RETRY_CONFIG, DATABASE_RETRY_CONFIG, API_RETRY_CONFIG
)
from error_handling.error_types import NetworkError, DatabaseError
from error_handling.health_checks import HealthCheckConfig
from error_handling.circuit_breaker import CircuitBreakerConfig


# Example 1: Basic Async Service with Full Error Handling
async def example_user_service():
    """Example user service with comprehensive error handling"""
    
    print("=== Example 1: User Service with Error Handling ===")
    
    # Initialize error handling system
    system = await initialize_error_system("user_service")
    
    @with_error_handling(operation_name="fetch_user")
    @with_retry(API_RETRY_CONFIG)
    @with_circuit_breaker("user_database")
    async def fetch_user(user_id: str):
        """Fetch user data with automatic error handling"""
        print(f"Fetching user {user_id}...")
        
        # Simulate database operations
        await asyncio.sleep(0.1)
        
        if random.random() < 0.3:
            raise DatabaseError("Database connection failed")
        
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com"
        }
    
    try:
        # Fetch users with automatic retry and circuit breaker protection
        for user_id in ["1", "2", "3", "error", "4"]:
            try:
                user = await fetch_user(user_id)
                print(f"✓ Successfully fetched: {user}")
            except Exception as e:
                print(f"✗ Failed to fetch user {user_id}: {e}")
    except Exception as e:
        print(f"Service error: {e}")
    
    # Get system status
    status = await system.get_system_status()
    print(f"System Status: {status['health']['overall_status']}")


# Example 2: Health Checks with Recovery Actions
async def example_health_monitoring():
    """Example health monitoring with automated recovery"""
    
    print("\n=== Example 2: Health Monitoring with Recovery ===")
    
    system = await initialize_error_system("monitored_service")
    
    # Add a custom health check
    async def custom_service_check():
        """Custom health check implementation"""
        # Simulate service health check
        await asyncio.sleep(0.1)
        return random.random() > 0.3  # 70% chance of being healthy
    
    from error_handling.health_checks import CustomHealthChecker, restart_service_action
    
    checker = CustomHealthChecker(
        name="custom_service",
        check_func=custom_service_check,
        config=HealthCheckConfig(
            interval=10,  # Check every 10 seconds
            failure_threshold=2,
            critical=True
        )
    )
    
    # Add recovery action
    checker.add_recovery_action(restart_service_action("custom_service"))
    
    system.health_manager.add_checker(checker)
    
    # Run health checks for a short period
    print("Running health checks for 30 seconds...")
    for i in range(6):  # 6 checks over 30 seconds
        await asyncio.sleep(5)
        results = await system.health_manager.check_all()
        
        for name, result in results.items():
            print(f"Health check '{name}': {result.status.value} - {result.message}")
    
    print(f"Overall health status: {system.health_manager.get_overall_status().value}")


# Example 3: Circuit Breaker with Fallback
async def example_circuit_breaker_fallback():
    """Example circuit breaker with fallback strategies"""
    
    print("\n=== Example 3: Circuit Breaker with Fallback ===")
    
    system = await initialize_error_system("api_service")
    
    # Define fallback data
    static_fallback = {
        "user_1": {"id": "1", "name": "Fallback User", "source": "cache"},
        "user_2": {"id": "2", "name": "Cached User", "source": "cache"}
    }
    
    async def primary_api_call(user_id: str):
        """Primary API call that might fail"""
        print(f"Calling primary API for user {user_id}...")
        
        await asyncio.sleep(0.2)
        
        if random.random() < 0.7:  # 70% failure rate
            raise NetworkError("Primary API unavailable")
        
        return {
            "id": user_id,
            "name": f"API User {user_id}",
            "source": "primary_api"
        }
    
    async def fallback_api_call(user_id: str):
        """Fallback API call"""
        print(f"Using fallback API for user {user_id}...")
        
        # Return static data if available
        if user_id in static_fallback:
            return static_fallback[user_id]
        
        # Return minimal data otherwise
        return {
            "id": user_id,
            "name": f"Default User {user_id}",
            "source": "default_fallback"
        }
    
    @with_error_handling(operation_name="user_lookup")
    @with_circuit_breaker("user_api", CircuitBreakerConfig(
        failure_threshold=3,
        timeout=10.0,
        success_threshold=2
    ))
    async def get_user_data(user_id: str):
        """Get user data with circuit breaker and fallback"""
        try:
            # Try primary API first
            return await primary_api_call(user_id)
        except Exception:
            # Use fallback if primary fails
            return await fallback_api_call(user_id)
    
    # Test the circuit breaker behavior
    print("Testing circuit breaker behavior...")
    for i in range(10):
        user_id = str(i % 3 + 1)
        try:
            user = await get_user_data(user_id)
            print(f"✓ Got user data: {user}")
        except Exception as e:
            print(f"✗ Failed to get user {user_id}: {e}")
        
        await asyncio.sleep(0.5)
    
    # Check circuit breaker states
    cb_states = system.circuit_breaker_registry.get_all_states()
    print("\nCircuit Breaker States:")
    for name, state in cb_states.items():
        print(f"  {name}: {state['state']} (failures: {state['metrics']['failed_calls']})")


# Example 4: Graceful Degradation
async def example_graceful_degradation():
    """Example graceful degradation system"""
    
    print("\n=== Example 4: Graceful Degradation ===")
    
    # Configure degradation system
    config = {
        'health_checks': {
            'checks': [
                {
                    'name': 'system_resources',
                    'type': 'resource',
                    'config': {'interval': 30}
                }
            ]
        },
        'degradation': {
            'services': [
                {
                    'name': 'payment_service',
                    'tier': 'critical',
                    'description': 'Payment processing service'
                },
                {
                    'name': 'analytics_service',
                    'tier': 'luxury',
                    'description': 'Analytics and reporting service'
                },
                {
                    'name': 'notification_service',
                    'tier': 'enhanced',
                    'description': 'Email and push notification service'
                }
            ],
            'rules': [
                {
                    'condition': 'error_rate > 5',
                    'target_level': 'limited_features',
                    'services_to_disable': ['analytics_service'],
                    'timeout_minutes': 15
                },
                {
                    'condition': 'error_rate > 10',
                    'target_level': 'essential_only',
                    'capacity_reduction': 0.5,
                    'timeout_minutes': 30
                }
            ]
        }
    }
    
    system = await initialize_error_system("service_with_degradation", config)
    
    # Register services for graceful degradation
    from error_handling.graceful_degradation import (
        ServiceInfo, GracefulDegradationManager
    )
    
    degradation_manager = GracefulDegradationManager(system.health_manager)
    
    # Define service functions
    @graceful_degradation(
        service_name="payment_service",
        tier=ServiceTier.CRITICAL
    )
    async def process_payment(amount: float):
        """Critical payment processing"""
        print(f"Processing payment: ${amount}")
        await asyncio.sleep(0.1)
        return {"status": "processed", "amount": amount}
    
    @graceful_degradation(
        service_name="analytics_service",
        tier=ServiceTier.LUXURY,
        fallback=lambda: {"analytics": "cached_data", "source": "cache"}
    )
    async def generate_analytics():
        """Non-critical analytics generation"""
        print("Generating analytics...")
        await asyncio.sleep(0.2)
        return {"data": "fresh_analytics", "timestamp": time.time()}
    
    @graceful_degradation(
        service_name="notification_service",
        tier=ServiceTier.IMPORTANT,
        fallback=lambda: {"status": "queued", "message": "Notifications queued"}
    )
    async def send_notification(message: str):
        """Important notification service"""
        print(f"Sending notification: {message}")
        await asyncio.sleep(0.1)
        return {"status": "sent", "message": message}
    
    # Test service behavior under different degradation levels
    print("Testing services...")
    
    # Normal operation
    print("\n--- Normal Operation ---")
    print(f"Current degradation level: {degradation_manager.get_degradation_level().value}")
    
    try:
        payment = await process_payment(100.0)
        analytics = await generate_analytics()
        notification = await send_notification("Welcome!")
        print(f"✓ All services working: payment={payment['status']}, analytics={analytics.get('source')}, notification={notification['status']}")
    except Exception as e:
        print(f"✗ Service failed: {e}")
    
    # Simulate high error rate to trigger degradation
    print("\n--- Simulating High Error Rate ---")
    
    # Artificially increase error rate in the system
    for _ in range(20):
        # Simulate errors
        pass
    
    # Check current state
    current_level = degradation_manager.get_degradation_level()
    print(f"Current degradation level: {current_level.value}")
    print(f"Enabled services: {degradation_manager.get_enabled_services()}")
    
    # Test services under degradation
    print("\n--- Testing Under Degradation ---")
    try:
        payment = await process_payment(50.0)
        print(f"✓ Payment service: {payment['status']}")
    except Exception as e:
        print(f"✗ Payment service failed: {e}")
    
    try:
        analytics = await generate_analytics()
        print(f"✓ Analytics service: {analytics.get('source')}")
    except Exception as e:
        print(f"✗ Analytics service failed: {e}")


# Example 5: Error Dashboard and Monitoring
async def example_error_dashboard():
    """Example error dashboard and monitoring"""
    
    print("\n=== Example 5: Error Dashboard and Monitoring ===")
    
    system = await initialize_error_system("dashboard_example")
    
    # Generate some test errors
    @with_error_handling(operation_name="risky_operation")
    async def risky_operation():
        """Operation that sometimes fails"""
        await asyncio.sleep(0.1)
        
        if random.random() < 0.4:  # 40% failure rate
            raise NetworkError("Network issue occurred")
        
        return {"status": "success", "data": "operation completed"}
    
    # Run multiple operations to generate data
    print("Generating test data...")
    for i in range(20):
        try:
            result = await risky_operation()
            print(f"✓ Operation {i+1}: {result['status']}")
        except Exception as e:
            print(f"✗ Operation {i+1}: {e}")
        
        await asyncio.sleep(0.2)
    
    # Wait a bit for dashboard to collect data
    await asyncio.sleep(2)
    
    # Get dashboard data
    dashboard_data = system.get_dashboard_data(force_refresh=True)
    
    print(f"\nDashboard Summary:")
    print(f"  Overall Health: {dashboard_data.get('health', {}).get('overall_status', 'unknown')}")
    print(f"  Total Errors: {dashboard_data.get('errors', {}).get('total_errors', 0)}")
    print(f"  Active Alerts: {dashboard_data.get('alerts', {}).get('total_active', 0)}")
    print(f"  Recent Error Rate: {dashboard_data.get('errors', {}).get('error_rate', 0):.2f}/min")
    
    # Generate report
    print(f"\nGenerating report...")
    report = system.generate_status_report(period_hours=1)
    print(f"Report:\n{report}")


# Example 6: Complete Service Integration
async def example_complete_service():
    """Example of complete service integration"""
    
    print("\n=== Example 6: Complete Service Integration ===")
    
    # Define comprehensive configuration
    service_config = {
        'health_checks': {
            'checks': [
                {
                    'name': 'database_health',
                    'type': 'database',
                    'config': {'interval': 30, 'critical': True}
                },
                {
                    'name': 'external_api',
                    'type': 'http',
                    'url': 'https://api.example.com/health',
                    'config': {'interval': 60}
                },
                {
                    'name': 'system_resources',
                    'type': 'resource',
                    'config': {'interval': 120}
                }
            ]
        },
        'circuit_breakers': {
            'services': [
                {
                    'name': 'payment_service',
                    'config': {'failure_threshold': 3, 'timeout': 30.0}
                },
                {
                    'name': 'notification_service',
                    'config': {'failure_threshold': 5, 'timeout': 60.0}
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
                    'name': 'advanced_analytics',
                    'tier': 'luxury',
                    'description': 'Advanced analytics features'
                }
            ],
            'rules': [
                {
                    'condition': 'overall_health_status == "unhealthy"',
                    'target_level': 'limited_features',
                    'timeout_minutes': 20
                }
            ]
        },
        'alerts': {
            'rules': [
                {
                    'name': 'high_error_rate',
                    'condition': 'error_rate > 8',
                    'severity': 'error',
                    'description': 'High error rate detected',
                    'notification_channels': ['console', 'log']
                },
                {
                    'name': 'service_unavailable',
                    'condition': 'overall_health_status == "unhealthy"',
                    'severity': 'critical',
                    'description': 'Service health is critical',
                    'notification_channels': ['console', 'log']
                }
            ]
        }
    }
    
    # Initialize the complete system
    system = await initialize_error_system("complete_service", service_config)
    
    # Define services with different tiers
    @graceful_degradation(
        service_name="core_payment",
        tier=ServiceTier.CRITICAL
    )
    @with_retry(DATABASE_RETRY_CONFIG)
    @with_circuit_breaker("payment_service")
    @with_error_handling(operation_name="process_payment")
    async def process_payment(amount: float, user_id: str):
        """Core payment processing service"""
        print(f"Processing payment: ${amount} for user {user_id}")
        
        await asyncio.sleep(0.1)  # Simulate processing
        
        if random.random() < 0.2:  # 20% failure rate
            raise DatabaseError("Payment database unavailable")
        
        return {
            "transaction_id": f"txn_{int(time.time())}",
            "amount": amount,
            "user_id": user_id,
            "status": "completed"
        }
    
    @graceful_degradation(
        service_name="advanced_analytics",
        tier=ServiceTier.LUXURY,
        fallback=lambda: {"data": "cached_analytics", "timestamp": time.time()}
    )
    @with_retry(NETWORK_RETRY_CONFIG)
    @with_error_handling(operation_name="generate_report")
    async def generate_analytics_report():
        """Advanced analytics (can be disabled during degradation)"""
        print("Generating analytics report...")
        
        await asyncio.sleep(0.2)
        
        if random.random() < 0.3:  # 30% failure rate
            raise NetworkError("Analytics service unavailable")
        
        return {
            "report_id": f"rpt_{int(time.time())}",
            "data": "comprehensive_analytics",
            "generated_at": time.time()
        }
    
    # Test the complete service
    print("Testing complete service integration...")
    
    # Normal operations
    print("\n--- Normal Operations ---")
    
    # Process payments (critical service)
    for i in range(3):
        try:
            result = await process_payment(100.0 + i * 50, f"user_{i+1}")
            print(f"✓ Payment {i+1}: {result['status']} (ID: {result['transaction_id']})")
        except Exception as e:
            print(f"✗ Payment {i+1} failed: {e}")
    
    # Generate analytics (non-critical service)
    try:
        report = await generate_analytics_report()
        print(f"✓ Analytics: {report['report_id']}")
    except Exception as e:
        print(f"✗ Analytics failed: {e}")
    
    # Check system status
    print("\n--- System Status ---")
    status = await system.get_system_status()
    
    print(f"Service: {status['service_name']}")
    print(f"Health: {status['health']['overall_status']}")
    print(f"Degradation: {status['degradation']['current_level']}")
    print(f"Active Alerts: {status['alerts']['active']}")
    print(f"Circuit Breakers: {len(status['circuit_breakers'])}")
    print(f"Recent Errors: {status['recent_errors']}")
    
    # Test under simulated failure conditions
    print("\n--- Simulating Failure Conditions ---")
    
    # Force some health checks to fail
    system.health_manager.checkers['database_health'].status = "unhealthy"
    
    # Check if degradation kicks in
    degradation_info = system.degradation_manager.get_degradation_info()
    print(f"Degradation level: {degradation_info['current_level']}")
    print(f"Enabled services: {degradation_info['enabled_services']}")


# Main execution
async def main():
    """Run all examples"""
    
    print("🚀 Error Handling System Examples")
    print("=" * 50)
    
    try:
        # Run each example
        await example_user_service()
        await asyncio.sleep(1)
        
        await example_health_monitoring()
        await asyncio.sleep(1)
        
        await example_circuit_breaker_fallback()
        await asyncio.sleep(1)
        
        await example_graceful_degradation()
        await asyncio.sleep(1)
        
        await example_error_dashboard()
        await asyncio.sleep(1)
        
        await example_complete_service()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())