"""
Base tool handler for Composio MCP Server.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import aiohttp
import structlog
from mcp.server.models import Tool
from mcp.types import CallToolResult

logger = structlog.get_logger()


class BaseToolHandler(ABC):
    """Base class for all tool handlers."""
    
    def __init__(self, settings, auth_manager, rate_limiter):
        """Initialize tool handler."""
        self.settings = settings
        self.auth_manager = auth_manager
        self.rate_limiter = rate_limiter
        self.name = self.__class__.__name__.replace("ToolHandler", "").lower()
        self.timeout = self._get_timeout()
        
        # HTTP session for API calls
        self.session = None
        
        logger.info(f"Tool handler initialized: {self.name}")
    
    def _get_timeout(self) -> int:
        """Get timeout for this tool's API calls."""
        tool_config = getattr(self.settings.tools, self.name, {})
        return tool_config.get("timeout", 30)
    
    async def initialize(self):
        """Initialize the tool handler (e.g., create HTTP session)."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_default_headers()
            )
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests."""
        headers = {
            "User-Agent": self.settings.tools.get(self.name, {}).get("user_agent", "Composio-MCP-Server/1.0"),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add tool-specific headers
        if self.name == "notion":
            headers["Notion-Version"] = self.settings.tools.notion.get("version", "2022-06-28")
        
        return headers
    
    def _get_api_url(self, endpoint: str = "") -> str:
        """Get API URL for the tool."""
        base_url = self.settings.tools.get(self.name, {}).get("api_url", "")
        if endpoint:
            return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        return base_url
    
    async def test_connection(self) -> bool:
        """Test connection to the external service."""
        try:
            if not self.session:
                await self.initialize()
            
            # Default test endpoint for each tool
            test_endpoint = self._get_test_endpoint()
            if not test_endpoint:
                return True  # No test needed
            
            async with self.session.get(test_endpoint) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"{self.name} connection test failed", error=str(e))
            return False
    
    def _get_test_endpoint(self) -> Optional[str]:
        """Get test endpoint for the tool. Override in subclasses."""
        return None
    
    @abstractmethod
    async def list_tools(self) -> List[Tool]:
        """List available tools for this handler."""
        pass
    
    @abstractmethod
    async def call_tool(self, request) -> CallToolResult:
        """Call a specific tool."""
        pass
    
    async def filter_tools_for_user(self, user_id: str, tools: List[Tool]) -> List[Tool]:
        """Filter tools based on user permissions."""
        # Default implementation - all tools available if user has basic access
        user_permissions = await self.auth_manager.get_user_permissions(user_id)
        
        if "admin" in user_permissions:
            return tools  # Admin gets all tools
        
        # Regular users get tools based on permissions
        filtered_tools = []
        for tool in tools:
            tool_name = tool.name.lower()
            
            # Define required permissions for each tool
            tool_permissions = self._get_tool_permissions()
            required_permissions = tool_permissions.get(tool_name, ["read"])
            
            if any(perm in user_permissions for perm in required_permissions):
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _get_tool_permissions(self) -> Dict[str, List[str]]:
        """Get required permissions for each tool. Override in subclasses."""
        return {}
    
    async def make_request(
        self, 
        method: str, 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with authentication and error handling."""
        try:
            if not self.session:
                await self.initialize()
            
            # Merge headers
            request_headers = self._get_default_headers()
            if headers:
                request_headers.update(headers)
            
            # Add authentication
            auth_headers = await self._get_auth_headers(user_id)
            if auth_headers:
                request_headers.update(auth_headers)
            
            # Make request
            url = self._get_api_url(endpoint)
            
            logger.debug(f"Making {method} request", url=url, endpoint=endpoint)
            
            async with self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                json=data if data else None,
                params=params
            ) as response:
                response_text = await response.text()
                
                # Log request details
                logger.debug(
                    f"{self.name} API request",
                    method=method,
                    url=url,
                    status=response.status,
                    response_length=len(response_text)
                )
                
                # Handle different response types
                try:
                    response_data = json.loads(response_text) if response_text else {}
                except json.JSONDecodeError:
                    response_data = {"raw_response": response_text}
                
                if response.status >= 400:
                    error_msg = response_data.get("message", response_data.get("error", "Unknown error"))
                    logger.error(
                        f"{self.name} API error",
                        status=response.status,
                        error=error_msg,
                        url=url
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg,
                        headers=response.headers
                    )
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"{self.name} HTTP request failed", error=str(e))
            raise
        except Exception as e:
            logger.error(f"{self.name} request failed", error=str(e))
            raise
    
    async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """Get authentication headers for the user. Override in subclasses."""
        return {}
    
    async def get_user_credentials(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's credentials for this tool."""
        if not user_id:
            return None
        
        return await self.auth_manager.get_tool_credentials(user_id, self.name)
    
    def _create_tool_result(self, content: Any, is_error: bool = False) -> CallToolResult:
        """Create standardized tool result."""
        if isinstance(content, dict):
            content_text = json.dumps(content, indent=2)
        elif isinstance(content, list):
            content_text = json.dumps(content, indent=2)
        else:
            content_text = str(content)
        
        return CallToolResult(
            content=[{
                "type": "text",
                "text": content_text
            }],
            isError=is_error
        )
    
    def _validate_required_params(self, params: Dict[str, Any], required: List[str]) -> List[str]:
        """Validate required parameters are present."""
        missing = []
        for param in required:
            if param not in params or not params[param]:
                missing.append(param)
        return missing
    
    async def _handle_rate_limiting(self, user_id: str, tool_name: str):
        """Handle rate limiting for the request."""
        if self.settings.rate_limit.enabled:
            # Record the request
            await self.rate_limiter.record_request(user_id, self.name)
            
            # Check if rate limited
            if not await self.rate_limiter.check_rate_limit(user_id, self.name):
                raise RateLimitError(f"Rate limit exceeded for {tool_name}")
    
    def _get_rate_limit_config(self) -> Dict[str, int]:
        """Get rate limit configuration for this tool."""
        return self.settings.rate_limit.tool_specific_limits.get(self.name, {})
    
    async def _paginate_results(self, initial_response: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle pagination for API responses. Override in subclasses if needed."""
        # Default implementation - return initial response items
        items_key = self._get_items_key()
        if items_key and items_key in initial_response:
            return initial_response[items_key]
        
        return [initial_response]
    
    def _get_items_key(self) -> str:
        """Get the key that contains items in API response. Override in subclasses."""
        return "items"
    
    def _extract_error_message(self, error: Exception) -> str:
        """Extract user-friendly error message from exception."""
        if hasattr(error, "message"):
            return error.message
        elif hasattr(error, "status"):
            return f"HTTP {error.status}: {str(error)}"
        else:
            return str(error)


class RateLimitError(Exception):
    """Rate limit exceeded exception."""
    pass


class ToolError(Exception):
    """Generic tool execution error."""
    pass


class AuthenticationError(Exception):
    """Authentication error."""
    pass