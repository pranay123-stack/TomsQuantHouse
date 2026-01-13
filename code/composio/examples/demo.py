#!/usr/bin/env python3
"""
Composio MCP Server - Interactive Demo
A hands-on demonstration of the server capabilities.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional

# Add the server directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.composio_server import ComposioMCPServer
from config.settings import Settings


class ComposioDemo:
    """Interactive demo for Composio MCP Server."""
    
    def __init__(self):
        self.server = None
        self.settings = None
        self.running = False
    
    async def initialize(self):
        """Initialize the demo."""
        print("🚀 Initializing Composio MCP Server Demo...")
        
        try:
            # Load configuration
            self.settings = Settings.load("config/config.json")
            print(f"✓ Configuration loaded (environment: {self.settings.environment})")
            
            # Initialize server
            self.server = ComposioMCPServer("config/config.json")
            print("✓ Server initialized")
            
            # Test server health
            health = await self.server.health_monitor.get_health_status()
            print(f"✓ Server health: {health.get('overall', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"✗ Initialization failed: {e}")
            return False
    
    async def demo_server_status(self):
        """Demonstrate server status monitoring."""
        print("\n📊 Server Status Demo")
        print("-" * 30)
        
        try:
            # Get server status
            status = await self.server._handle_server_status()
            status_data = json.loads(status.content[0]["text"])
            
            print(f"Server: {status_data.get('server', 'unknown')}")
            print(f"Status: {status_data.get('status', 'unknown')}")
            print(f"Version: {status_data.get('version', 'unknown')}")
            print(f"Uptime: {status_data.get('uptime_seconds', 0):.0f} seconds")
            print(f"Tools loaded: {status_data.get('tools_loaded', 0)}")
            
            # Get detailed health information
            health = await self.server.health_monitor.get_health_status()
            print(f"\nSystem Health:")
            print(f"  CPU Usage: {health.get('system', {}).get('cpu', {}).get('usage_percent', 0):.1f}%")
            print(f"  Memory Usage: {health.get('system', {}).get('memory', {}).get('usage_percent', 0):.1f}%")
            print(f"  Disk Usage: {health.get('system', {}).get('disk', {}).get('usage_percent', 0):.1f}%")
            
            return True
            
        except Exception as e:
            print(f"✗ Error getting server status: {e}")
            return False
    
    async def demo_tools_listing(self):
        """Demonstrate tool listing capabilities."""
        print("\n🔧 Tools Listing Demo")
        print("-" * 30)
        
        try:
            # List all available tools
            tools_result = await self.server.server.list_tools({})
            tools = tools_result.tools
            
            print(f"Total tools available: {len(tools)}")
            
            # Group tools by category
            tools_by_category = {}
            for tool in tools:
                if ":" in tool.name:
                    category = tool.name.split(":")[0]
                    if category not in tools_by_category:
                        tools_by_category[category] = []
                    tools_by_category[category].append(tool)
                else:
                    if "server" not in tools_by_category:
                        tools_by_category["server"] = []
                    tools_by_category["server"].append(tool)
            
            # Display tools by category
            for category, category_tools in tools_by_category.items():
                print(f"\n{category.upper()} Tools ({len(category_tools)}):")
                for tool in category_tools[:5]:  # Show first 5 tools per category
                    print(f"  - {tool.name}")
                    print(f"    {tool.description}")
                if len(category_tools) > 5:
                    print(f"    ... and {len(category_tools) - 5} more")
            
            return True
            
        except Exception as e:
            print(f"✗ Error listing tools: {e}")
            return False
    
    async def demo_github_integration(self):
        """Demonstrate GitHub integration."""
        print("\n🐙 GitHub Integration Demo")
        print("-" * 30)
        
        try:
            # Get GitHub tools
            github_handler = self.server.tool_handlers.get("github")
            if not github_handler:
                print("✗ GitHub handler not available")
                return False
            
            # List GitHub tools
            github_tools = await github_handler.list_tools()
            print(f"GitHub tools available: {len(github_tools)}")
            
            for tool in github_tools[:3]:
                print(f"  - {tool.name}: {tool.description}")
            
            # Simulate a tool call (will fail without real credentials)
            print("\nSimulating GitHub repository info request...")
            
            # Create mock request
            class MockRequest:
                def __init__(self):
                    self.params = MockParams()
            
            class MockParams:
                def __init__(self):
                    self.name = "github_repository_info"
                    self.arguments = {
                        "owner": "microsoft",
                        "repo": "vscode"
                    }
            
            mock_request = MockRequest()
            
            # This would normally make an API call, but will fail without credentials
            # result = await github_handler.call_tool(mock_request)
            print("  (Note: Real API call requires GitHub token in user credentials)")
            print("  ✓ GitHub integration demo completed")
            
            return True
            
        except Exception as e:
            print(f"✗ Error in GitHub demo: {e}")
            return False
    
    async def demo_trading_tools(self):
        """Demonstrate trading tools."""
        print("\n📈 Trading Tools Demo")
        print("-" * 30)
        
        try:
            # Show QuantConnect tools
            qc_handler = self.server.tool_handlers.get("quantconnect")
            if qc_handler:
                qc_tools = await qc_handler.list_tools()
                print(f"QuantConnect tools: {len(qc_tools)}")
                for tool in qc_tools[:3]:
                    print(f"  - {tool.name}")
                    print(f"    {tool.description}")
            
            # Show Abacus.AI tools
            abacus_handler = self.server.tool_handlers.get("abacus_ai")
            if abacus_handler:
                abacus_tools = await abacus_handler.list_tools()
                print(f"\nAbacus.AI tools: {len(abacus_tools)}")
                for tool in abacus_tools[:3]:
                    print(f"  - {tool.name}")
                    print(f"    {tool.description}")
            
            print("\nTrading-specific features:")
            print("  ✓ Algorithmic strategy backtesting")
            print("  ✓ Live trading deployment")
            print("  ✓ AI-powered market analysis")
            print("  ✓ Portfolio optimization")
            print("  ✓ Risk management")
            
            return True
            
        except Exception as e:
            print(f"✗ Error in trading demo: {e}")
            return False
    
    async def demo_rate_limiting(self):
        """Demonstrate rate limiting system."""
        print("\n⏱️  Rate Limiting Demo")
        print("-" * 30)
        
        try:
            rate_limiter = self.server.rate_limiter
            
            # Test rate limit status
            user_id = "demo_user"
            tool_name = "github"
            
            print("Initial rate limit status:")
            status = await rate_limiter.get_status(user_id, tool_name)
            for limit_type, limit_info in status.get("limits", {}).items():
                print(f"  {limit_type}: {limit_info['current_count']}/{limit_info['max_requests']}")
            
            # Simulate some requests
            print("\nSimulating requests...")
            for i in range(3):
                allowed = await rate_limiter.check_rate_limit(user_id, tool_name)
                if allowed:
                    await rate_limiter.record_request(user_id, tool_name)
                    print(f"  Request {i+1}: ✓ Allowed")
                else:
                    print(f"  Request {i+1}: ✗ Rate limited")
            
            # Show updated status
            print("\nRate limit status after requests:")
            updated_status = await rate_limiter.get_status(user_id, tool_name)
            for limit_type, limit_info in updated_status.get("limits", {}).items():
                print(f"  {limit_type}: {limit_info['current_count']}/{limit_info['max_requests']}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error in rate limiting demo: {e}")
            return False
    
    async def demo_metrics_monitoring(self):
        """Demonstrate metrics and monitoring."""
        print("\n📊 Metrics & Monitoring Demo")
        print("-" * 30)
        
        try:
            # Get server metrics
            metrics = await self.server.metrics_collector.get_metrics()
            
            print("Server Metrics:")
            print(f"  Uptime: {metrics.get('server', {}).get('uptime_hours', 0):.1f} hours")
            print(f"  Total requests: {metrics.get('requests', {}).get('total', 0)}")
            print(f"  Success rate: {metrics.get('requests', {}).get('success_rate', 0):.1f}%")
            print(f"  Error rate: {metrics.get('requests', {}).get('error_rate', 0):.1f}%")
            
            # Show top tools
            top_tools = metrics.get('top_tools', [])
            if top_tools:
                print(f"\nTop Tools:")
                for tool_info in top_tools[:5]:
                    print(f"  - {tool_info['tool']}: {tool_info['requests']} requests")
            
            # Show system metrics
            system_info = metrics.get('system', {})
            print(f"\nSystem Performance:")
            print(f"  CPU: {system_info.get('cpu', {}).get('usage_percent', 0):.1f}%")
            print(f"  Memory: {system_info.get('memory', {}).get('usage_percent', 0):.1f}%")
            
            # Create detailed report
            report = await self.server.metrics_collector.create_metrics_report()
            print(f"\nOverall Performance Score: {report.get('summary', {}).get('performance_score', 'N/A')}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error in metrics demo: {e}")
            return False
    
    async def demo_configuration(self):
        """Demonstrate configuration management."""
        print("\n⚙️  Configuration Demo")
        print("-" * 30)
        
        try:
            # Show current configuration
            print("Current Configuration:")
            print(f"  Environment: {self.settings.environment}")
            print(f"  Debug mode: {self.settings.debug}")
            print(f"  Database: {self.settings.database.url}")
            print(f"  Redis: {self.settings.redis.url}")
            
            # Show feature flags
            print(f"\nFeature Flags:")
            for feature, enabled in self.settings.features.items():
                status = "✓" if enabled else "✗"
                print(f"  {status} {feature}")
            
            # Show tool configurations
            print(f"\nTool Configurations:")
            tools_config = self.settings.tools
            for tool_name in ["github", "slack", "quantconnect", "abacus_ai"]:
                if hasattr(tools_config, tool_name):
                    tool_config = getattr(tools_config, tool_name)
                    enabled = tool_config.get("enabled", False)
                    status = "✓" if enabled else "✗"
                    print(f"  {status} {tool_name}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error in configuration demo: {e}")
            return False
    
    async def run_interactive_demo(self):
        """Run the interactive demo."""
        print("🎮 Composio MCP Server - Interactive Demo")
        print("=" * 50)
        print("This demo will showcase the key features of the Composio MCP Server")
        print("Press Enter to continue through each step, or Ctrl+C to exit.\n")
        
        demos = [
            ("Server Status", self.demo_server_status),
            ("Tools Listing", self.demo_tools_listing),
            ("GitHub Integration", self.demo_github_integration),
            ("Trading Tools", self.demo_trading_tools),
            ("Rate Limiting", self.demo_rate_limiting),
            ("Metrics & Monitoring", self.demo_metrics_monitoring),
            ("Configuration", self.demo_configuration)
        ]
        
        for i, (demo_name, demo_func) in enumerate(demos, 1):
            print(f"\n{i}. {demo_name}")
            input("Press Enter to run this demo...")
            
            try:
                success = await demo_func()
                if success:
                    print(f"✓ {demo_name} completed successfully")
                else:
                    print(f"✗ {demo_name} failed")
            except KeyboardInterrupt:
                print("\nDemo interrupted by user")
                break
            except Exception as e:
                print(f"✗ {demo_name} error: {e}")
            
            if i < len(demos):
                input("\nPress Enter for next demo...")
        
        print("\n" + "=" * 50)
        print("🎉 Interactive Demo Completed!")
        print("\nNext steps:")
        print("1. Configure your tool credentials in the auth system")
        print("2. Start the server: python server/composio_server.py")
        print("3. Integrate with your MCP client")
        print("4. Monitor server health and performance")
    
    async def run_quick_demo(self):
        """Run a quick non-interactive demo."""
        print("⚡ Composio MCP Server - Quick Demo")
        print("=" * 50)
        
        demos = [
            self.demo_server_status,
            self.demo_tools_listing,
            self.demo_trading_tools,
            self.demo_rate_limiting,
            self.demo_metrics_monitoring
        ]
        
        for demo_func in demos:
            try:
                await demo_func()
            except Exception as e:
                print(f"✗ Demo error: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 Quick Demo Completed!")


async def main():
    """Main demo function."""
    demo = ComposioDemo()
    
    # Initialize
    if not await demo.initialize():
        print("Failed to initialize demo. Exiting.")
        return
    
    # Check if running interactively
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await demo.run_interactive_demo()
    else:
        await demo.run_quick_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDemo interrupted. Goodbye!")
    except Exception as e:
        print(f"Demo failed: {e}")
        sys.exit(1)