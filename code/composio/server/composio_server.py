#!/usr/bin/env python3
"""
Composio MCP Server - Main Server Implementation
A comprehensive Model Context Protocol server with external tool integrations.
"""

import asyncio
import json
import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from mcp.server import Server
from mcp.server.models import Tool
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    GetPromptRequest,
    GetPromptResult,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListToolsRequest,
    ListToolsResult,
    ReadResourceRequest,
    ReadResourceResult,
    Tool as ToolType,
)
from prometheus_client import Counter, Histogram, start_http_server

from config.settings import Settings
from auth.manager import AuthManager
from auth.jwt_handler import JWTHandler
from monitoring.health import HealthMonitor
from monitoring.metrics import MetricsCollector
from tools.base import BaseToolHandler
from tools.github import GitHubToolHandler
from tools.slack import SlackToolHandler
from tools.telegram import TelegramToolHandler
from tools.notion import NotionToolHandler
from tools.quantconnect import QuantConnectToolHandler
from tools.abacus_ai import AbacusAIToolHandler
from tools.rate_limiter import RateLimiter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class ComposioMCPServer:
    """Main Composio MCP Server with comprehensive tool integration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the server with configuration."""
        self.config_path = config_path or "config/config.json"
        self.settings = Settings.load(self.config_path)
        self.server = Server("composio-mcp-server")
        
        # Initialize core components
        self.auth_manager = AuthManager(self.settings)
        self.jwt_handler = JWTHandler(self.settings)
        self.health_monitor = HealthMonitor(self.settings)
        self.metrics_collector = MetricsCollector(self.settings)
        self.rate_limiter = RateLimiter(self.settings)
        
        # Tool handlers registry
        self.tool_handlers: Dict[str, BaseToolHandler] = {}
        self._initialize_tool_handlers()
        
        # Metrics
        self.request_count = Counter('mcp_requests_total', 'Total MCP requests', ['method', 'tool'])
        self.request_duration = Histogram('mcp_request_duration_seconds', 'Request duration', ['method', 'tool'])
        
        logger.info("Composio MCP Server initialized", config_path=self.config_path)
    
    def _initialize_tool_handlers(self):
        """Initialize all available tool handlers."""
        handlers = [
            GitHubToolHandler(self.settings, self.auth_manager, self.rate_limiter),
            SlackToolHandler(self.settings, self.auth_manager, self.rate_limiter),
            TelegramToolHandler(self.settings, self.auth_manager, self.rate_limiter),
            NotionToolHandler(self.settings, self.auth_manager, self.rate_limiter),
            QuantConnectToolHandler(self.settings, self.auth_manager, self.rate_limiter),
            AbacusAIToolHandler(self.settings, self.auth_manager, self.rate_limiter),
        ]
        
        for handler in handlers:
            self.tool_handlers[handler.name] = handler
            logger.info(f"Loaded tool handler: {handler.name}")
    
    def _register_server_tools(self):
        """Register server-level tools."""
        
        @self.server.list_tools()
        async def handle_list_tools(request: ListToolsRequest) -> ListToolsResult:
            """List all available tools."""
            all_tools = []
            
            for handler in self.tool_handlers.values():
                tools = await handler.list_tools()
                all_tools.extend(tools)
            
            # Add server management tools
            server_tools = [
                Tool(
                    name="server_status",
                    description="Get server status and health information",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="list_user_tools",
                    description="List tools available to the authenticated user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID (optional, uses authenticated user if not provided)"
                            }
                        },
                    },
                ),
                Tool(
                    name="rate_limit_status",
                    description="Check current rate limit status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "User ID (optional, uses authenticated user if not provided)"
                            }
                        },
                    },
                ),
            ]
            
            all_tools.extend(server_tools)
            
            return ListToolsResult(tools=all_tools)
        
        @self.server.call_tool()
        async def handle_call_tool(request: CallToolRequest) -> CallToolResult:
            """Handle tool execution requests."""
            import time
            
            start_time = time.time()
            tool_name = request.params.name
            
            try:
                # Check rate limits
                user_id = await self._get_user_id_from_context(request)
                if not await self.rate_limiter.check_rate_limit(user_id, tool_name):
                    return CallToolResult(
                        content=[
                            {
                                "type": "text",
                                "text": "Rate limit exceeded. Please try again later."
                            }
                        ],
                        isError=True,
                    )
                
                # Route to appropriate handler or execute server tool
                if tool_name == "server_status":
                    result = await self._handle_server_status()
                elif tool_name == "list_user_tools":
                    result = await self._handle_list_user_tools(request.params.arguments or {})
                elif tool_name == "rate_limit_status":
                    result = await self._handle_rate_limit_status(request.params.arguments or {})
                elif tool_name in self.tool_handlers:
                    handler = self.tool_handlers[tool_name]
                    result = await handler.call_tool(request)
                else:
                    return CallToolResult(
                        content=[
                            {
                                "type": "text",
                                "text": f"Unknown tool: {tool_name}"
                            }
                        ],
                        isError=True,
                    )
                
                # Record metrics
                duration = time.time() - start_time
                self.request_count.labels(method="call_tool", tool=tool_name).inc()
                self.request_duration.labels(method="call_tool", tool=tool_name).observe(duration)
                
                return result
                
            except Exception as e:
                logger.error("Tool execution failed", tool=tool_name, error=str(e))
                return CallToolResult(
                    content=[
                        {
                            "type": "text",
                            "text": f"Tool execution failed: {str(e)}"
                        }
                    ],
                    isError=True,
                )
        
        @self.server.list_prompts()
        async def handle_list_prompts(request: ListPromptsRequest) -> ListPromptsResult:
            """List available prompts."""
            prompts = []
            
            # Add trading-specific prompts
            prompts.extend([
                {
                    "name": "trading_analysis",
                    "description": "Generate comprehensive trading analysis",
                    "arguments": [
                        {
                            "name": "symbol",
                            "description": "Trading symbol to analyze",
                            "required": True
                        },
                        {
                            "name": "timeframe",
                            "description": "Analysis timeframe",
                            "required": False
                        }
                    ]
                },
                {
                    "name": "portfolio_review",
                    "description": "Review and optimize portfolio allocation",
                    "arguments": [
                        {
                            "name": "portfolio_id",
                            "description": "Portfolio identifier",
                            "required": True
                        }
                    ]
                }
            ])
            
            return ListPromptsResult(prompts=prompts)
        
        @self.server.get_prompt()
        async def handle_get_prompt(request: GetPromptRequest) -> GetPromptResult:
            """Get a specific prompt."""
            if request.params.name == "trading_analysis":
                symbol = request.params.arguments.get("symbol", "AAPL")
                timeframe = request.params.arguments.get("timeframe", "1D")
                
                prompt = f"""
                Provide a comprehensive trading analysis for {symbol} on {timeframe} timeframe.
                Include:
                1. Technical analysis with key levels
                2. Fundamental factors
                3. Risk assessment
                4. Trading recommendations
                5. Entry and exit points
                
                Use available tools to gather the latest data and provide actionable insights.
                """
                
                return GetPromptResult(description="Comprehensive trading analysis", arguments=[
                    {"name": "symbol", "value": symbol},
                    {"name": "timeframe", "value": timeframe}
                ], messages=[{"role": "user", "content": {"type": "text", "text": prompt}}])
            
            # Default fallback
            return GetPromptResult(description="No specific prompt found", arguments=[], messages=[])
        
        @self.server.list_resources()
        async def handle_list_resources(request: ListResourcesRequest) -> ListResourcesResult:
            """List available resources."""
            resources = []
            
            # Add server resources
            resources.extend([
                {
                    "uri": "composio://server/health",
                    "name": "Server Health",
                    "description": "Current server health status",
                    "mimeType": "application/json"
                },
                {
                    "uri": "composio://server/metrics",
                    "name": "Server Metrics",
                    "description": "Server performance metrics",
                    "mimeType": "application/json"
                },
                {
                    "uri": "composio://server/tools",
                    "name": "Available Tools",
                    "description": "List of all available tools",
                    "mimeType": "application/json"
                }
            ])
            
            return ListResourcesResult(resources=resources)
        
        @self.server.read_resource()
        async def handle_read_resource(request: ReadResourceRequest) -> ReadResourceResult:
            """Read a specific resource."""
            uri = request.params.uri
            
            if uri == "composio://server/health":
                health_data = await self.health_monitor.get_health_status()
                return ReadResourceResult(
                    contents=[{
                        "mimeType": "application/json",
                        "text": json.dumps(health_data, indent=2)
                    }]
                )
            
            elif uri == "composio://server/metrics":
                metrics_data = await self.metrics_collector.get_metrics()
                return ReadResourceResult(
                    contents=[{
                        "mimeType": "application/json",
                        "text": json.dumps(metrics_data, indent=2)
                    }]
                )
            
            elif uri == "composio://server/tools":
                tools_data = []
                for handler in self.tool_handlers.values():
                    tools = await handler.list_tools()
                    tools_data.extend([{
                        "handler": handler.name,
                        "tools": [tool.model_dump() for tool in tools]
                    }])
                
                return ReadResourceResult(
                    contents=[{
                        "mimeType": "application/json",
                        "text": json.dumps(tools_data, indent=2)
                    }]
                )
            
            return ReadResourceResult(contents=[], isError=True)
    
    async def _get_user_id_from_context(self, request: CallToolRequest) -> Optional[str]:
        """Extract user ID from request context."""
        # In a real implementation, this would extract from authentication headers
        # For now, we'll use a placeholder or the authenticated user's token
        return "default_user"
    
    async def _handle_server_status(self) -> CallToolResult:
        """Handle server status requests."""
        health = await self.health_monitor.get_health_status()
        uptime = await self.health_monitor.get_uptime()
        
        status_info = {
            "server": "composio-mcp-server",
            "status": "healthy" if health["overall"] == "healthy" else "unhealthy",
            "uptime_seconds": uptime,
            "health": health,
            "version": "1.0.0",
            "tools_loaded": len(self.tool_handlers),
            "timestamp": self.health_monitor.get_current_timestamp()
        }
        
        return CallToolResult(
            content=[{
                "type": "text",
                "text": json.dumps(status_info, indent=2)
            }]
        )
    
    async def _handle_list_user_tools(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle user-specific tool listing."""
        user_id = args.get("user_id") or await self._get_user_id_from_context(
            CallToolRequest(params={"name": "list_user_tools"})
        )
        
        # Get tools available to user based on permissions
        available_tools = []
        for handler in self.tool_handlers.values():
            tools = await handler.list_tools()
            # Filter based on user permissions
            filtered_tools = await handler.filter_tools_for_user(user_id, tools)
            available_tools.extend(filtered_tools)
        
        return CallToolResult(
            content=[{
                "type": "text",
                "text": json.dumps({
                    "user_id": user_id,
                    "tools_count": len(available_tools),
                    "tools": [tool.model_dump() for tool in available_tools]
                }, indent=2)
            }]
        )
    
    async def _handle_rate_limit_status(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle rate limit status requests."""
        user_id = args.get("user_id") or "default_user"
        rate_limit_status = await self.rate_limiter.get_status(user_id)
        
        return CallToolResult(
            content=[{
                "type": "text",
                "text": json.dumps({
                    "user_id": user_id,
                    "rate_limit": rate_limit_status
                }, indent=2)
            }]
        )
    
    @asynccontextmanager
    async def lifespan(self):
        """Server lifespan context manager."""
        logger.info("Starting Composio MCP Server...")
        
        # Start metrics server if enabled
        if self.settings.metrics.enabled:
            start_http_server(self.settings.metrics.port)
            logger.info(f"Metrics server started on port {self.settings.metrics.port}")
        
        # Initialize health monitoring
        await self.health_monitor.start()
        
        # Test external connections
        await self._test_connections()
        
        yield
        
        # Cleanup
        logger.info("Shutting down Composio MCP Server...")
        await self.health_monitor.stop()
    
    async def _test_connections(self):
        """Test external service connections."""
        logger.info("Testing external service connections...")
        
        for handler in self.tool_handlers.values():
            try:
                if await handler.test_connection():
                    logger.info(f"✓ {handler.name} connection successful")
                else:
                    logger.warning(f"⚠ {handler.name} connection failed")
            except Exception as e:
                logger.error(f"✗ {handler.name} connection error: {e}")
    
    async def run(self):
        """Run the server with stdio transport."""
        self._register_server_tools()
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.lifespan,
            )


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Composio MCP Server")
    parser.add_argument(
        "--config",
        default="config/config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Metrics server port"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    # Load and start server
    server = ComposioMCPServer(config_path=args.config)
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error("Server failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()