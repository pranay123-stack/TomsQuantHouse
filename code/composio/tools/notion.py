"""
Notion tool handler for Composio MCP Server.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from mcp.server.models import Tool
from mcp.types import CallToolResult

from .base import BaseToolHandler, AuthenticationError

logger = structlog.get_logger()


class NotionToolHandler(BaseToolHandler):
    """Notion API tool handler."""
    
    def __init__(self, settings, auth_manager, rate_limiter):
        super().__init__(settings, auth_manager, rate_limiter)
        self.notion_config = settings.tools.notion
    
    def _get_test_endpoint(self) -> str:
        """Notion API test endpoint."""
        return "users/me"
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Notion API requests."""
        headers = {
            "Notion-Version": self.notion_config.get("version", "2022-06-28"),
            "Content-Type": "application/json"
        }
        return headers
    
    async def list_tools(self) -> List[Tool]:
        """List available Notion tools."""
        return [
            Tool(
                name="notion_create_page",
                description="Create a new page in Notion",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page ID or database ID"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties"
                        },
                        "children": {
                            "type": "array",
                            "description": "Child blocks"
                        },
                        "icon": {
                            "type": "object",
                            "description": "Page icon"
                        },
                        "cover": {
                            "type": "object",
                            "description": "Page cover"
                        }
                    },
                    "required": ["parent_id"]
                }
            ),
            Tool(
                name="notion_get_page",
                description="Get page content from Notion",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            Tool(
                name="notion_create_database",
                description="Create a new database in Notion",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page ID"
                        },
                        "title": {
                            "type": "string",
                            "description": "Database title"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Database properties schema"
                        }
                    },
                    "required": ["parent_id", "title"]
                }
            ),
            Tool(
                name="notion_query_database",
                description="Query a Notion database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Query filter"
                        },
                        "sorts": {
                            "type": "array",
                            "description": "Sort options"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 100
                        }
                    },
                    "required": ["database_id"]
                }
            ),
            Tool(
                name="notion_search",
                description="Search Notion pages and databases",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Result filter"
                        },
                        "sort": {
                            "type": "object",
                            "description": "Sort options"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 100
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="notion_create_block",
                description="Create a new block",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "block_id": {
                            "type": "string",
                            "description": "Parent block ID"
                        },
                        "block_type": {
                            "type": "string",
                            "description": "Block type"
                        },
                        "content": {
                            "type": "object",
                            "description": "Block content"
                        }
                    },
                    "required": ["block_id", "block_type", "content"]
                }
            ),
            Tool(
                name="notion_update_page",
                description="Update a page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Page properties to update"
                        },
                        "icon": {
                            "type": "object",
                            "description": "Page icon"
                        },
                        "cover": {
                            "type": "object",
                            "description": "Page cover"
                        }
                    },
                    "required": ["page_id"]
                }
            )
        ]
    
    def _get_tool_permissions(self) -> Dict[str, List[str]]:
        """Get required permissions for each Notion tool."""
        return {
            "notion_create_page": ["write"],
            "notion_get_page": ["read"],
            "notion_create_database": ["write"],
            "notion_query_database": ["read"],
            "notion_search": ["read"],
            "notion_create_block": ["write"],
            "notion_update_page": ["write"]
        }
    
    async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """Get Notion authentication headers."""
        if not user_id:
            return {}
        
        credentials = await self.get_user_credentials(user_id)
        if not credentials or "token" not in credentials:
            raise AuthenticationError("Notion integration token not found in user credentials")
        
        return {
            "Authorization": f"Bearer {credentials['token']}"
        }
    
    async def call_tool(self, request) -> CallToolResult:
        """Handle Notion tool execution."""
        tool_name = request.params.name
        params = request.params.arguments or {}
        
        try:
            await self._handle_rate_limiting(request, tool_name)
            
            if tool_name == "notion_create_page":
                return await self._handle_create_page(params)
            elif tool_name == "notion_get_page":
                return await self._handle_get_page(params)
            elif tool_name == "notion_create_database":
                return await self._handle_create_database(params)
            elif tool_name == "notion_query_database":
                return await self._handle_query_database(params)
            elif tool_name == "notion_search":
                return await self._handle_search(params)
            elif tool_name == "notion_create_block":
                return await self._handle_create_block(params)
            elif tool_name == "notion_update_page":
                return await self._handle_update_page(params)
            else:
                return self._create_tool_result(f"Unknown Notion tool: {tool_name}", is_error=True)
                
        except Exception as e:
            logger.error("Notion tool execution failed", tool=tool_name, error=str(e))
            return self._create_tool_result(f"Tool execution failed: {str(e)}", is_error=True)
    
    async def _handle_create_page(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create page request."""
        required = ["parent_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            page_data = {
                "parent": {"page_id": params["parent_id"]},
                "properties": params.get("properties", {}),
                "children": params.get("children", [])
            }
            
            if "icon" in params:
                page_data["icon"] = params["icon"]
            if "cover" in params:
                page_data["cover"] = params["cover"]
            
            response = await self.make_request("POST", "pages", data=page_data)
            
            result = {
                "id": response.get("id"),
                "created_time": response.get("created_time"),
                "last_edited_time": response.get("last_edited_time"),
                "created_by": response.get("created_by"),
                "last_edited_by": response.get("last_edited_by"),
                "cover": response.get("cover"),
                "icon": response.get("icon"),
                "parent": response.get("parent"),
                "archived": response.get("archived"),
                "properties": response.get("properties"),
                "url": response.get("url")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create page: {str(e)}", is_error=True)
    
    async def _handle_get_page(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get page request."""
        required = ["page_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request("GET", f"pages/{params['page_id']}")
            
            result = {
                "id": response.get("id"),
                "created_time": response.get("created_time"),
                "last_edited_time": response.get("last_edited_time"),
                "created_by": response.get("created_by"),
                "last_edited_by": response.get("last_edited_by"),
                "cover": response.get("cover"),
                "icon": response.get("icon"),
                "parent": response.get("parent"),
                "archived": response.get("archived"),
                "properties": response.get("properties"),
                "url": response.get("url")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get page: {str(e)}", is_error=True)
    
    async def _handle_create_database(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create database request."""
        required = ["parent_id", "title"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            database_data = {
                "parent": {"page_id": params["parent_id"]},
                "title": [{"type": "text", "text": {"content": params["title"]}}],
                "properties": params.get("properties", {})
            }
            
            response = await self.make_request("POST", "databases", data=database_data)
            
            result = {
                "id": response.get("id"),
                "created_time": response.get("created_time"),
                "last_edited_time": response.get("last_edited_time"),
                "created_by": response.get("created_by"),
                "last_edited_by": response.get("last_edited_by"),
                "title": response.get("title"),
                "description": response.get("description"),
                "is_inline": response.get("is_inline"),
                "properties": response.get("properties"),
                "parent": response.get("parent"),
                "url": response.get("url")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create database: {str(e)}", is_error=True)
    
    async def _handle_query_database(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle query database request."""
        required = ["database_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            query_data = {
                "page_size": min(params.get("page_size", 100), 100)
            }
            
            if "filter" in params:
                query_data["filter"] = params["filter"]
            if "sorts" in params:
                query_data["sorts"] = params["sorts"]
            
            response = await self.make_request("POST", f"databases/{params['database_id']}/query", data=query_data)
            
            results = []
            for page in response.get("results", []):
                results.append({
                    "id": page.get("id"),
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time"),
                    "properties": page.get("properties"),
                    "url": page.get("url")
                })
            
            return self._create_tool_result({
                "results": results,
                "has_more": response.get("has_more"),
                "next_cursor": response.get("next_cursor")
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to query database: {str(e)}", is_error=True)
    
    async def _handle_search(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle search request."""
        required = ["query"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            search_data = {
                "query": params["query"],
                "page_size": min(params.get("page_size", 100), 100)
            }
            
            if "filter" in params:
                search_data["filter"] = params["filter"]
            if "sort" in params:
                search_data["sort"] = params["sort"]
            
            response = await self.make_request("POST", "search", data=search_data)
            
            results = []
            for item in response.get("results", []):
                item_type = item.get("object")
                
                if item_type == "page":
                    results.append({
                        "id": item.get("id"),
                        "object": item_type,
                        "created_time": item.get("created_time"),
                        "last_edited_time": item.get("last_edited_time"),
                        "created_by": item.get("created_by"),
                        "last_edited_by": item.get("last_edited_by"),
                        "cover": item.get("cover"),
                        "icon": item.get("icon"),
                        "parent": item.get("parent"),
                        "archived": item.get("archived"),
                        "properties": item.get("properties"),
                        "url": item.get("url")
                    })
                elif item_type == "database":
                    results.append({
                        "id": item.get("id"),
                        "object": item_type,
                        "created_time": item.get("created_time"),
                        "last_edited_time": item.get("last_edited_time"),
                        "created_by": item.get("created_by"),
                        "last_edited_by": item.get("last_edited_by"),
                        "title": item.get("title"),
                        "description": item.get("description"),
                        "is_inline": item.get("is_inline"),
                        "properties": item.get("properties"),
                        "parent": item.get("parent"),
                        "url": item.get("url")
                    })
            
            return self._create_tool_result({
                "results": results,
                "has_more": response.get("has_more"),
                "next_cursor": response.get("next_cursor")
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to search: {str(e)}", is_error=True)
    
    async def _handle_create_block(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create block request."""
        required = ["block_id", "block_type", "content"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            block_data = {
                "object": "block",
                "type": params["block_type"],
                params["block_type"]: params["content"]
            }
            
            response = await self.make_request("POST", f"blocks/{params['block_id']}/children", data=[block_data])
            
            created_block = response[0] if response else {}
            
            result = {
                "id": created_block.get("id"),
                "type": created_block.get("type"),
                "created_time": created_block.get("created_time"),
                "last_edited_time": created_block.get("last_edited_time"),
                "created_by": created_block.get("created_by"),
                "last_edited_by": created_block.get("last_edited_by"),
                "has_children": created_block.get("has_children"),
                "archived": created_block.get("archived")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create block: {str(e)}", is_error=True)
    
    async def _handle_update_page(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle update page request."""
        required = ["page_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            update_data = {}
            
            if "properties" in params:
                update_data["properties"] = params["properties"]
            if "icon" in params:
                update_data["icon"] = params["icon"]
            if "cover" in params:
                update_data["cover"] = params["cover"]
            
            response = await self.make_request("PATCH", f"pages/{params['page_id']}", data=update_data)
            
            result = {
                "id": response.get("id"),
                "created_time": response.get("created_time"),
                "last_edited_time": response.get("last_edited_time"),
                "created_by": response.get("created_by"),
                "last_edited_by": response.get("last_edited_by"),
                "cover": response.get("cover"),
                "icon": response.get("icon"),
                "parent": response.get("parent"),
                "archived": response.get("archived"),
                "properties": response.get("properties"),
                "url": response.get("url")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to update page: {str(e)}", is_error=True)