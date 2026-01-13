"""
Telegram tool handler for Composio MCP Server.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from mcp.server.models import Tool
from mcp.types import CallToolResult

from .base import BaseToolHandler, AuthenticationError

logger = structlog.get_logger()


class TelegramToolHandler(BaseToolHandler):
    """Telegram Bot API tool handler."""
    
    def __init__(self, settings, auth_manager, rate_limiter):
        super().__init__(settings, auth_manager, rate_limiter)
        self.telegram_config = settings.tools.telegram
    
    def _get_test_endpoint(self) -> str:
        """Telegram API test endpoint."""
        return "getMe"
    
    async def list_tools(self) -> List[Tool]:
        """List available Telegram tools."""
        return [
            Tool(
                name="telegram_send_message",
                description="Send a message to a Telegram chat",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {
                            "type": "string",
                            "description": "Chat ID or username (e.g., @username or -123456789)"
                        },
                        "text": {
                            "type": "string",
                            "description": "Message text"
                        },
                        "parse_mode": {
                            "type": "string",
                            "enum": ["HTML", "Markdown", "MarkdownV2"],
                            "description": "Text parsing mode"
                        },
                        "disable_web_page_preview": {
                            "type": "boolean",
                            "description": "Disable link previews",
                            "default": False
                        },
                        "disable_notification": {
                            "type": "boolean",
                            "description": "Send silently",
                            "default": False
                        }
                    },
                    "required": ["chat_id", "text"]
                }
            ),
            Tool(
                name="telegram_get_me",
                description="Get bot information",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="telegram_get_chat",
                description="Get chat information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {
                            "type": "string",
                            "description": "Chat ID"
                        }
                    },
                    "required": ["chat_id"]
                }
            ),
            Tool(
                name="telegram_get_updates",
                description="Get bot updates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "offset": {
                            "type": "integer",
                            "description": "Update ID to start from"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of updates to retrieve",
                            "default": 100
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout for long polling",
                            "default": 0
                        }
                    }
                }
            )
        ]
    
    def _get_tool_permissions(self) -> Dict[str, List[str]]:
        """Get required permissions for each Telegram tool."""
        return {
            "telegram_send_message": ["write"],
            "telegram_get_me": ["read"],
            "telegram_get_chat": ["read"],
            "telegram_get_updates": ["read"]
        }
    
    async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """Get Telegram authentication headers."""
        if not user_id:
            return {}
        
        credentials = await self.get_user_credentials(user_id)
        if not credentials or "bot_token" not in credentials:
            raise AuthenticationError("Telegram bot token not found in user credentials")
        
        return {}
    
    def _get_api_url(self, endpoint: str = "") -> str:
        """Get Telegram API URL."""
        if not user_id:
            return ""
        
        # Note: This needs the actual bot token, which we don't have here
        # In a real implementation, the token would be stored in credentials
        return f"https://api.telegram.org/bot{credentials.get('bot_token', '')}/{endpoint}"
    
    async def call_tool(self, request) -> CallToolResult:
        """Handle Telegram tool execution."""
        tool_name = request.params.name
        params = request.params.arguments or {}
        
        try:
            await self._handle_rate_limiting(request, tool_name)
            
            if tool_name == "telegram_send_message":
                return await self._handle_send_message(params)
            elif tool_name == "telegram_get_me":
                return await self._handle_get_me(params)
            elif tool_name == "telegram_get_chat":
                return await self._handle_get_chat(params)
            elif tool_name == "telegram_get_updates":
                return await self._handle_get_updates(params)
            else:
                return self._create_tool_result(f"Unknown Telegram tool: {tool_name}", is_error=True)
                
        except Exception as e:
            logger.error("Telegram tool execution failed", tool=tool_name, error=str(e))
            return self._create_tool_result(f"Tool execution failed: {str(e)}", is_error=True)
    
    async def _handle_send_message(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle send message request."""
        required = ["chat_id", "text"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            data = {
                "chat_id": params["chat_id"],
                "text": params["text"]
            }
            
            if "parse_mode" in params:
                data["parse_mode"] = params["parse_mode"]
            if "disable_web_page_preview" in params:
                data["disable_web_page_preview"] = params["disable_web_page_preview"]
            if "disable_notification" in params:
                data["disable_notification"] = params["disable_notification"]
            
            response = await self.make_request("POST", "sendMessage", data=data)
            
            if not response.get("ok"):
                return self._create_tool_result(f"Telegram API error: {response.get('description')}", is_error=True)
            
            message = response.get("result", {})
            return self._create_tool_result({
                "message_id": message.get("message_id"),
                "date": message.get("date"),
                "chat": message.get("chat", {}),
                "text": message.get("text")
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to send message: {str(e)}", is_error=True)
    
    async def _handle_get_me(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get bot info request."""
        try:
            response = await self.make_request("GET", "getMe")
            
            if not response.get("ok"):
                return self._create_tool_result(f"Telegram API error: {response.get('description')}", is_error=True)
            
            bot_info = response.get("result", {})
            return self._create_tool_result({
                "id": bot_info.get("id"),
                "is_bot": bot_info.get("is_bot"),
                "first_name": bot_info.get("first_name"),
                "username": bot_info.get("username"),
                "can_join_groups": bot_info.get("can_join_groups"),
                "can_read_all_group_messages": bot_info.get("can_read_all_group_messages"),
                "supports_inline_queries": bot_info.get("supports_inline_queries")
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get bot info: {str(e)}", is_error=True)
    
    async def _handle_get_chat(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get chat info request."""
        required = ["chat_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request("GET", "getChat", params={"chat_id": params["chat_id"]})
            
            if not response.get("ok"):
                return self._create_tool_result(f"Telegram API error: {response.get('description')}", is_error=True)
            
            chat_info = response.get("result", {})
            return self._create_tool_result({
                "id": chat_info.get("id"),
                "type": chat_info.get("type"),
                "title": chat_info.get("title"),
                "username": chat_info.get("username"),
                "first_name": chat_info.get("first_name"),
                "description": chat_info.get("description"),
                "invite_link": chat_info.get("invite_link")
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get chat info: {str(e)}", is_error=True)
    
    async def _handle_get_updates(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get updates request."""
        try:
            query_params = {}
            
            if "offset" in params:
                query_params["offset"] = params["offset"]
            if "limit" in params:
                query_params["limit"] = min(params["limit"], 100)
            if "timeout" in params:
                query_params["timeout"] = params["timeout"]
            
            response = await self.make_request("GET", "getUpdates", params=query_params)
            
            if not response.get("ok"):
                return self._create_tool_result(f"Telegram API error: {response.get('description')}", is_error=True)
            
            updates = response.get("result", [])
            
            return self._create_tool_result({
                "updates_count": len(updates),
                "updates": updates
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get updates: {str(e)}", is_error=True)