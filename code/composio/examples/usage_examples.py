#!/usr/bin/env python3
"""
Composio MCP Server - Usage Examples
Demonstrates how to use the server and its tools programmatically.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List

# Add the server directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.composio_server import ComposioMCPServer
from config.settings import Settings
from auth.manager import AuthManager
from tools.rate_limiter import RateLimiter


async def example_basic_usage():
    """Basic server usage example."""
    print("=== Basic Server Usage Example ===")
    
    # Load configuration
    settings = Settings.load("config/config.json")
    
    # Initialize server
    server = ComposioMCPServer("config/config.json")
    
    try:
        # Test server status
        print("Testing server status...")
        status_result = await server._handle_server_status()
        print(f"Server status: {status_result.content[0]['text']}")
        
        # Test tool listing
        print("\nTesting tool listing...")
        tools_result = await server.server.list_tools({"jsonrpc": "2.0"})
        tools_data = json.loads(tools_result.tools[0].name if hasattr(tools_result, 'tools') else "{}")
        print(f"Available tools: {len(tools_result.tools)}")
        
        for tool in tools_result.tools[:5]:  # Show first 5 tools
            print(f"  - {tool.name}: {tool.description}")
        
        print("✓ Basic usage example completed")
        
    except Exception as e:
        print(f"✗ Error in basic usage: {e}")


async def example_authentication():
    """Authentication system example."""
    print("\n=== Authentication Example ===")
    
    # Load configuration
    settings = Settings.load("config/config.json")
    auth_manager = AuthManager(settings)
    
    try:
        # Create database tables
        await auth_manager.create_database()
        print("✓ Database initialized")
        
        # Register a user
        from auth.manager import UserCredentials
        credentials = UserCredentials(
            username="demo_user",
            password="secure_password_123",
            tool_credentials={
                "github": {"token": "ghp_example_token"},
                "slack": {"bot_token": "xoxb-example-token"},
                "quantconnect": {"token": "qc_example_token"}
            }
        )
        
        register_result = await auth_manager.register_user(credentials)
        if register_result["success"]:
            print(f"✓ User registered: {register_result['username']}")
            
            # Authenticate user
            auth_result = await auth_manager.authenticate_user("demo_user", "secure_password_123")
            if auth_result:
                print(f"✓ User authenticated: {auth_result['user']['username']}")
                print(f"  Access token: {auth_result['tokens']['access_token'][:50]}...")
                
                # Test token verification
                user_info = await auth_manager.verify_token(auth_result['tokens']['access_token'])
                if user_info:
                    print(f"✓ Token verified for user: {user_info['username']}")
                    print(f"  Permissions: {user_info['permissions']}")
                
        print("✓ Authentication example completed")
        
    except Exception as e:
        print(f"✗ Error in authentication: {e}")


async def example_github_integration():
    """GitHub integration example."""
    print("\n=== GitHub Integration Example ===")
    
    try:
        from tools.github import GitHubToolHandler
        from auth.manager import AuthManager
        
        settings = Settings.load("config/config.json")
        auth_manager = AuthManager(settings)
        rate_limiter = RateLimiter(settings)
        
        github_handler = GitHubToolHandler(settings, auth_manager, rate_limiter)
        
        # Test connection (will fail without real token)
        print("Testing GitHub connection...")
        connection_ok = await github_handler.test_connection()
        print(f"Connection status: {'OK' if connection_ok else 'Failed (expected without token)'}")
        
        # List available tools
        tools = await github_handler.list_tools()
        print(f"✓ GitHub tools available: {len(tools)}")
        
        for tool in tools[:3]:  # Show first 3 tools
            print(f"  - {tool.name}: {tool.description}")
        
        print("✓ GitHub integration example completed")
        
    except Exception as e:
        print(f"✗ Error in GitHub integration: {e}")


async def example_trading_tools():
    """Trading tools example."""
    print("\n=== Trading Tools Example ===")
    
    try:
        from tools.quantconnect import QuantConnectToolHandler
        from tools.abacus_ai import AbacusAIToolHandler
        from auth.manager import AuthManager
        
        settings = Settings.load("config/config.json")
        auth_manager = AuthManager(settings)
        rate_limiter = RateLimiter(settings)
        
        # QuantConnect handler
        qc_handler = QuantConnectToolHandler(settings, auth_manager, rate_limiter)
        qc_tools = await qc_handler.list_tools()
        print(f"✓ QuantConnect tools: {len(qc_tools)}")
        
        # Abacus.AI handler
        abacus_handler = AbacusAIToolHandler(settings, auth_manager, rate_limiter)
        abacus_tools = await abacus_handler.list_tools()
        print(f"✓ Abacus.AI tools: {len(abacus_tools)}")
        
        # Show some trading tools
        print("\nSample trading tools:")
        for tool in (qc_tools + abacus_tools)[:5]:
            print(f"  - {tool.name}: {tool.description}")
        
        print("✓ Trading tools example completed")
        
    except Exception as e:
        print(f"✗ Error in trading tools: {e}")


async def example_rate_limiting():
    """Rate limiting system example."""
    print("\n=== Rate Limiting Example ===")
    
    try:
        from tools.rate_limiter import RateLimiter
        
        settings = Settings.load("config/config.json")
        rate_limiter = RateLimiter(settings)
        
        user_id = "demo_user"
        tool_name = "github"
        
        # Check initial rate limit status
        status = await rate_limiter.get_status(user_id, tool_name)
        print(f"Initial rate limit status for {user_id}/{tool_name}:")
        print(json.dumps(status, indent=2))
        
        # Test rate limiting
        print("\nTesting rate limiting...")
        for i in range(3):
            allowed = await rate_limiter.check_rate_limit(user_id, tool_name)
            print(f"Request {i+1}: {'Allowed' if allowed else 'Rate Limited'}")
            
            if allowed:
                await rate_limiter.record_request(user_id, tool_name)
        
        # Check status after requests
        status_after = await rate_limiter.get_status(user_id, tool_name)
        print(f"\nRate limit status after requests:")
        for limit_type, limit_info in status_after.get("limits", {}).items():
            print(f"  {limit_type}: {limit_info['current_count']}/{limit_info['max_requests']}")
        
        # Test global stats
        global_stats = await rate_limiter.get_global_stats()
        print(f"\nGlobal rate limiting stats:")
        print(json.dumps(global_stats, indent=2))
        
        print("✓ Rate limiting example completed")
        
    except Exception as e:
        print(f"✗ Error in rate limiting: {e}")


async def example_monitoring():
    """Monitoring system example."""
    print("\n=== Monitoring System Example ===")
    
    try:
        from monitoring.health import HealthMonitor
        from monitoring.metrics import MetricsCollector
        
        settings = Settings.load("config/config.json")
        
        # Health monitoring
        health_monitor = HealthMonitor(settings)
        health_status = await health_monitor.get_health_status()
        print("✓ Health status:")
        print(f"  Overall: {health_status.get('overall', 'unknown')}")
        print(f"  Uptime: {health_status.get('uptime_hours', 0)} hours")
        
        # System metrics
        system_info = health_status.get("system", {})
        print(f"  CPU Usage: {system_info.get('cpu', {}).get('usage_percent', 0)}%")
        print(f"  Memory Usage: {system_info.get('memory', {}).get('usage_percent', 0)}%")
        
        # Metrics collection
        metrics_collector = MetricsCollector(settings)
        
        # Record some sample metrics
        await metrics_collector.record_request("github", "user123", "success", 1.5)
        await metrics_collector.record_request("slack", "user456", "success", 0.8)
        await metrics_collector.record_request("telegram", "user789", "failed", 2.1)
        
        # Get metrics
        metrics = await metrics_collector.get_metrics()
        print("\n✓ Sample metrics:")
        print(f"  Total requests: {metrics.get('requests', {}).get('total', 0)}")
        print(f"  Error rate: {metrics.get('requests', {}).get('error_rate', 0)}%")
        
        # Create detailed report
        report = await metrics_collector.create_metrics_report()
        print(f"\n✓ Performance score: {report.get('summary', {}).get('performance_score', 'N/A')}")
        
        print("✓ Monitoring example completed")
        
    except Exception as e:
        print(f"✗ Error in monitoring: {e}")


async def example_user_workflow():
    """Complete user workflow example."""
    print("\n=== Complete User Workflow Example ===")
    
    try:
        settings = Settings.load("config/config.json")
        auth_manager = AuthManager(settings)
        rate_limiter = RateLimiter(settings)
        
        # Simulate user registration and authentication
        from auth.manager import UserCredentials
        
        print("1. User registration...")
        credentials = UserCredentials(
            username="trader_alice",
            password="secure_trading_password",
            tool_credentials={
                "github": {"token": "ghp_workflow_token"},
                "slack": {"bot_token": "xoxb-workflow-token"},
                "quantconnect": {"token": "qc_workflow_token"},
                "abacus_ai": {"api_key": "abacus_workflow_key"}
            }
        )
        
        register_result = await auth_manager.register_user(credentials)
        if register_result["success"]:
            print(f"   ✓ Registered: {register_result['username']}")
        
        print("\n2. User authentication...")
        auth_result = await auth_manager.authenticate_user("trader_alice", "secure_trading_password")
        if auth_result:
            user_id = auth_result["user"]["id"]
            print(f"   ✓ Authenticated: {auth_result['user']['username']}")
            print(f"   ✓ User ID: {user_id}")
        
        print("\n3. Checking tool permissions...")
        permissions = await auth_manager.get_user_permissions(user_id)
        print(f"   ✓ User permissions: {list(permissions)}")
        
        print("\n4. Testing rate limits...")
        for tool in ["github", "quantconnect", "abacus_ai"]:
            status = await rate_limiter.get_status(user_id, tool)
            limits = status.get("limits", {})
            if limits:
                print(f"   ✓ {tool} limits: {limits.get('requests_per_hour', {}).get('max_requests', 'N/A')}/hour")
        
        print("\n5. Simulating tool usage...")
        
        # Simulate successful API calls
        await rate_limiter.record_request(user_id, "github")
        await rate_limiter.record_request(user_id, "quantconnect")
        await rate_limiter.record_request(user_id, "abacus_ai")
        
        # Check final rate limit status
        print("\n6. Final rate limit status...")
        for tool in ["github", "quantconnect"]:
            status = await rate_limiter.get_status(user_id, tool)
            limits = status.get("limits", {})
            for limit_type, limit_info in limits.items():
                used = limit_info.get('current_count', 0)
                max_allowed = limit_info.get('max_requests', 0)
                print(f"   ✓ {tool} {limit_type}: {used}/{max_allowed}")
        
        print("✓ Complete user workflow example finished")
        
    except Exception as e:
        print(f"✗ Error in user workflow: {e}")


async def example_configuration_validation():
    """Configuration validation example."""
    print("\n=== Configuration Validation Example ===")
    
    try:
        # Test with development config
        print("1. Testing development configuration...")
        dev_settings = Settings.load("config/config.example.json")
        dev_issues = dev_settings.validate()
        
        if dev_issues:
            print(f"   Issues found: {len(dev_issues)}")
            for issue in dev_issues:
                print(f"   - {issue}")
        else:
            print("   ✓ No issues found")
        
        # Test environment-specific settings
        print(f"\n2. Environment settings:")
        print(f"   Environment: {dev_settings.environment}")
        print(f"   Debug mode: {dev_settings.debug}")
        print(f"   Database URL: {dev_settings.database.url}")
        print(f"   Redis URL: {dev_settings.redis.url}")
        print(f"   Features enabled: {list(dev_settings.features.keys())}")
        
        # Test tool configurations
        print(f"\n3. Tool configurations:")
        tools_config = dev_settings.tools
        for tool_name in ["github", "slack", "quantconnect"]:
            if hasattr(tools_config, tool_name):
                tool_config = getattr(tools_config, tool_name)
                enabled = tool_config.get("enabled", False)
                rate_limit = tool_config.get("rate_limit", "N/A")
                print(f"   ✓ {tool_name}: enabled={enabled}, rate_limit={rate_limit}")
        
        # Test rate limiting configuration
        print(f"\n4. Rate limiting configuration:")
        rate_config = dev_settings.rate_limit
        print(f"   Enabled: {rate_config.enabled}")
        print(f"   Default limits: {list(rate_config.default_limits.keys())}")
        print(f"   Tool-specific limits: {list(rate_config.tool_specific_limits.keys())}")
        
        print("✓ Configuration validation example completed")
        
    except Exception as e:
        print(f"✗ Error in configuration validation: {e}")


async def main():
    """Run all examples."""
    print("Composio MCP Server - Usage Examples")
    print("=" * 50)
    
    examples = [
        example_configuration_validation,
        example_basic_usage,
        example_authentication,
        example_github_integration,
        example_trading_tools,
        example_rate_limiting,
        example_monitoring,
        example_user_workflow
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Example failed with error: {e}")
    
    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())