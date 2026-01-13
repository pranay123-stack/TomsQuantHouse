"""
Slack tool handler for Composio MCP Server.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from mcp.server.models import Tool
from mcp.types import CallToolResult

from .base import BaseToolHandler, AuthenticationError, ToolError

logger = structlog.get_logger()


class SlackToolHandler(BaseToolHandler):
    """Slack API tool handler."""
    
    def __init__(self, settings, auth_manager, rate_limiter):
        super().__init__(settings, auth_manager, rate_limiter)
        self.slack_config = settings.tools.slack
        self.api_version = "1.0.0"
    
    def _get_test_endpoint(self) -> str:
        """Slack API test endpoint."""
        return "https://slack.com/api/auth.test"
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for Slack API requests."""
        headers = {
            "Authorization": "Bearer placeholder",  # Will be overridden in _get_auth_headers
            "Content-Type": "application/json"
        }
        return headers
    
    async def list_tools(self) -> List[Tool]:
        """List available Slack tools."""
        return [
            Tool(
                name="slack_send_message",
                description="Send a message to a Slack channel or user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name (e.g., #general, @username)"
                        },
                        "text": {
                            "type": "string",
                            "description": "Message text"
                        },
                        "blocks": {
                            "type": "array",
                            "description": "Slack blocks for rich messages"
                        },
                        "attachments": {
                            "type": "array",
                            "description": "Message attachments"
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Thread timestamp to reply in thread"
                        },
                        "reply_broadcast": {
                            "type": "boolean",
                            "description": "Whether to broadcast the reply"
                        }
                    },
                    "required": ["channel", "text"]
                }
            ),
            Tool(
                name="slack_list_channels",
                description="List all Slack channels",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "types": {
                            "type": "string",
                            "description": "Comma-separated channel types (public_channel,private_channel,mpim,im)",
                            "default": "public_channel,private_channel"
                        },
                        "exclude_archived": {
                            "type": "boolean",
                            "description": "Exclude archived channels",
                            "default": True
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of channels to return",
                            "default": 100
                        }
                    }
                }
            ),
            Tool(
                name="slack_get_channel_info",
                description="Get information about a specific Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID"
                        },
                        "include_num_members": {
                            "type": "boolean",
                            "description": "Include the number of members",
                            "default": False
                        }
                    },
                    "required": ["channel"]
                }
            ),
            Tool(
                name="slack_list_users",
                description="List all users in the Slack workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "include_deleted": {
                            "type": "boolean",
                            "description": "Include deleted users",
                            "default": False
                        },
                        "include_restricted": {
                            "type": "boolean",
                            "description": "Include restricted users",
                            "default": False
                        }
                    }
                }
            ),
            Tool(
                name="slack_get_user_info",
                description="Get information about a specific Slack user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "string",
                            "description": "User ID or username"
                        }
                    },
                    "required": ["user"]
                }
            ),
            Tool(
                name="slack_upload_file",
                description="Upload a file to Slack",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channels": {
                            "type": "string",
                            "description": "Comma-separated channel IDs"
                        },
                        "file": {
                            "type": "string",
                            "description": "File content (base64 encoded for binary files)"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Filename"
                        },
                        "title": {
                            "type": "string",
                            "description": "File title"
                        },
                        "initial_comment": {
                            "type": "string",
                            "description": "Initial comment"
                        }
                    },
                    "required": ["channels", "file", "filename"]
                }
            ),
            Tool(
                name="slack_create_channel",
                description="Create a new Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Channel name (without #)"
                        },
                        "is_private": {
                            "type": "boolean",
                            "description": "Create private channel",
                            "default": False
                        }
                    },
                    "required": ["name"]
                }
            ),
            Tool(
                name="slack_set_channel_topic",
                description="Set the topic of a Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Channel topic"
                        }
                    },
                    "required": ["channel", "topic"]
                }
            ),
            Tool(
                name="slack_search_messages",
                description="Search for messages in Slack",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["timestamp", "score"],
                            "description": "Sort by timestamp or score"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 20,
                            "maximum": 100
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number",
                            "default": 1
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    
    def _get_tool_permissions(self) -> Dict[str, List[str]]:
        """Get required permissions for each Slack tool."""
        return {
            "slack_send_message": ["write"],
            "slack_list_channels": ["read"],
            "slack_get_channel_info": ["read"],
            "slack_list_users": ["read"],
            "slack_get_user_info": ["read"],
            "slack_upload_file": ["write"],
            "slack_create_channel": ["write"],
            "slack_set_channel_topic": ["write"],
            "slack_search_messages": ["read"]
        }
    
    async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """Get Slack authentication headers."""
        if not user_id:
            return {}
        
        credentials = await self.get_user_credentials(user_id)
        if not credentials or "bot_token" not in credentials:
            raise AuthenticationError("Slack bot token not found in user credentials")
        
        return {
            "Authorization": f"Bearer {credentials['bot_token']}"
        }
    
    async def call_tool(self, request) -> CallToolResult:
        """Handle Slack tool execution."""
        tool_name = request.params.name
        params = request.params.arguments or {}
        
        try:
            # Handle rate limiting
            await self._handle_rate_limiting(request, tool_name)
            
            # Route to appropriate handler
            if tool_name == "slack_send_message":
                return await self._handle_send_message(params)
            elif tool_name == "slack_list_channels":
                return await self._handle_list_channels(params)
            elif tool_name == "slack_get_channel_info":
                return await self._handle_get_channel_info(params)
            elif tool_name == "slack_list_users":
                return await self._handle_list_users(params)
            elif tool_name == "slack_get_user_info":
                return await self._handle_get_user_info(params)
            elif tool_name == "slack_upload_file":
                return await self._handle_upload_file(params)
            elif tool_name == "slack_create_channel":
                return await self._handle_create_channel(params)
            elif tool_name == "slack_set_channel_topic":
                return await self._handle_set_channel_topic(params)
            elif tool_name == "slack_search_messages":
                return await self._handle_search_messages(params)
            else:
                return self._create_tool_result(f"Unknown Slack tool: {tool_name}", is_error=True)
                
        except AuthenticationError as e:
            logger.error("Slack authentication error", error=str(e))
            return self._create_tool_result(f"Authentication failed: {str(e)}", is_error=True)
        except Exception as e:
            logger.error("Slack tool execution failed", tool=tool_name, error=str(e))
            return self._create_tool_result(f"Tool execution failed: {str(e)}", is_error=True)
    
    async def _handle_send_message(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle send message request."""
        required = ["channel", "text"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            # Prepare message data
            message_data = {
                "channel": params["channel"],
                "text": params["text"]
            }
            
            # Add optional parameters
            if "blocks" in params:
                message_data["blocks"] = params["blocks"]
            if "attachments" in params:
                message_data["attachments"] = params["attachments"]
            if "thread_ts" in params:
                message_data["thread_ts"] = params["thread_ts"]
            if "reply_broadcast" in params:
                message_data["reply_broadcast"] = params["reply_broadcast"]
            
            response = await self.make_request(
                "POST",
                "chat.postMessage",
                data=message_data,
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            result = {
                "message_id": response.get("ts"),
                "channel": response.get("channel"),
                "message": response.get("message", {})
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to send message: {str(e)}", is_error=True)
    
    async def _handle_list_channels(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle list channels request."""
        try:
            query_params = {}
            
            if "types" in params:
                query_params["types"] = params["types"]
            if "exclude_archived" in params:
                query_params["exclude_archived"] = str(params["exclude_archived"]).lower()
            if "limit" in params:
                query_params["limit"] = params["limit"]
            
            response = await self.make_request(
                "GET",
                "conversations.list",
                params=query_params,
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            channels = []
            for channel in response.get("channels", []):
                channels.append({
                    "id": channel.get("id"),
                    "name": channel.get("name"),
                    "is_channel": channel.get("is_channel"),
                    "is_group": channel.get("is_group"),
                    "is_im": channel.get("is_im"),
                    "is_mpim": channel.get("is_mpim"),
                    "is_private": channel.get("is_private"),
                    "is_archived": channel.get("is_archived"),
                    "is_general": channel.get("is_general"),
                    "unlinked": channel.get("unlinked"),
                    "name_normalized": channel.get("name_normalized"),
                    "created": channel.get("created"),
                    "is_creator": channel.get("is_creator"),
                    "is_ext_shared": channel.get("is_ext_shared"),
                    "is_org_shared": channel.get("is_org_shared"),
                    "pending_shared": channel.get("pending_shared"),
                    "context_team_id": channel.get("context_team_id"),
                    "updated": channel.get("updated"),
                    "parent_conversation": channel.get("parent_conversation"),
                    "creator": channel.get("creator"),
                    "is_ext_shared": channel.get("is_ext_shared"),
                    "shared_team_ids": channel.get("shared_team_ids", []),
                    "pending_connected_team_ids": channel.get("pending_connected_team_ids", [])
                })
            
            return self._create_tool_result({
                "channels": channels,
                "response_metadata": response.get("response_metadata", {})
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to list channels: {str(e)}", is_error=True)
    
    async def _handle_get_channel_info(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get channel info request."""
        required = ["channel"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            query_params = {"channel": params["channel"]}
            
            if "include_num_members" in params:
                query_params["include_num_members"] = str(params["include_num_members"]).lower()
            
            response = await self.make_request(
                "GET",
                "conversations.info",
                params=query_params,
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            channel = response.get("channel", {})
            
            channel_info = {
                "id": channel.get("id"),
                "name": channel.get("name"),
                "is_channel": channel.get("is_channel"),
                "is_group": channel.get("is_group"),
                "is_im": channel.get("is_im"),
                "is_mpim": channel.get("is_mpim"),
                "is_private": channel.get("is_private"),
                "is_archived": channel.get("is_archived"),
                "is_general": channel.get("is_general"),
                "unlinked": channel.get("unlinked"),
                "name_normalized": channel.get("name_normalized"),
                "created": channel.get("created"),
                "is_creator": channel.get("is_creator"),
                "is_ext_shared": channel.get("is_ext_shared"),
                "is_org_shared": channel.get("is_org_shared"),
                "pending_shared": channel.get("pending_shared"),
                "context_team_id": channel.get("context_team_id"),
                "updated": channel.get("updated"),
                "topic": {
                    "value": channel.get("topic", {}).get("value"),
                    "creator": channel.get("topic", {}).get("creator"),
                    "last_set": channel.get("topic", {}).get("last_set")
                },
                "purpose": {
                    "value": channel.get("purpose", {}).get("value"),
                    "creator": channel.get("purpose", {}).get("creator"),
                    "last_set": channel.get("purpose", {}).get("last_set")
                },
                "num_members": channel.get("num_members")
            }
            
            return self._create_tool_result(channel_info)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get channel info: {str(e)}", is_error=True)
    
    async def _handle_list_users(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle list users request."""
        try:
            query_params = {}
            
            if "include_deleted" in params:
                query_params["include_deleted"] = str(params["include_deleted"]).lower()
            if "include_restricted" in params:
                query_params["include_restricted"] = str(params["include_restricted"]).lower()
            
            response = await self.make_request(
                "GET",
                "users.list",
                params=query_params,
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            users = []
            for user in response.get("members", []):
                users.append({
                    "id": user.get("id"),
                    "team_id": user.get("team_id"),
                    "name": user.get("name"),
                    "deleted": user.get("deleted"),
                    "color": user.get("color"),
                    "real_name": user.get("real_name"),
                    "tz": user.get("tz"),
                    "tz_label": user.get("tz_label"),
                    "tz_offset": user.get("tz_offset"),
                    "profile": {
                        "title": user.get("profile", {}).get("title"),
                        "phone": user.get("profile", {}).get("phone"),
                        "skype": user.get("profile", {}).get("skype"),
                        "real_name": user.get("profile", {}).get("real_name"),
                        "real_name_normalized": user.get("profile", {}).get("real_name_normalized"),
                        "display_name": user.get("profile", {}).get("display_name"),
                        "display_name_normalized": user.get("profile", {}).get("display_name_normalized"),
                        "fields": user.get("profile", {}).get("fields"),
                        "status_text": user.get("profile", {}).get("status_text"),
                        "status_emoji": user.get("profile", {}).get("status_emoji"),
                        "status_expiration": user.get("profile", {}).get("status_expiration"),
                        "avatar_hash": user.get("profile", {}).get("avatar_hash"),
                        "email": user.get("profile", {}).get("email"),
                        "first_name": user.get("profile", {}).get("first_name"),
                        "last_name": user.get("profile", {}).get("last_name"),
                        "image_24": user.get("profile", {}).get("image_24"),
                        "image_32": user.get("profile", {}).get("image_32"),
                        "image_48": user.get("profile", {}).get("image_48"),
                        "image_72": user.get("profile", {}).get("image_72"),
                        "image_192": user.get("profile", {}).get("image_192"),
                        "image_512": user.get("profile", {}).get("image_512")
                    },
                    "is_admin": user.get("is_admin"),
                    "is_owner": user.get("is_owner"),
                    "is_primary_owner": user.get("is_primary_owner"),
                    "is_restricted": user.get("is_restricted"),
                    "is_ultra_restricted": user.get("is_ultra_restricted"),
                    "is_bot": user.get("is_bot"),
                    "updated": user.get("updated"),
                    "is_app_user": user.get("is_app_user"),
                    "has_2fa": user.get("has_2fa")
                })
            
            return self._create_tool_result({
                "users": users,
                "cache_ts": response.get("cache_ts"),
                "response_metadata": response.get("response_metadata", {})
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to list users: {str(e)}", is_error=True)
    
    async def _handle_get_user_info(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get user info request."""
        required = ["user"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request(
                "GET",
                "users.info",
                params={"user": params["user"]},
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            user = response.get("user", {})
            
            user_info = {
                "id": user.get("id"),
                "team_id": user.get("team_id"),
                "name": user.get("name"),
                "deleted": user.get("deleted"),
                "color": user.get("color"),
                "real_name": user.get("real_name"),
                "tz": user.get("tz"),
                "tz_label": user.get("tz_label"),
                "tz_offset": user.get("tz_offset"),
                "profile": user.get("profile", {}),
                "is_admin": user.get("is_admin"),
                "is_owner": user.get("is_owner"),
                "is_primary_owner": user.get("is_primary_owner"),
                "is_restricted": user.get("is_restricted"),
                "is_ultra_restricted": user.get("is_ultra_restricted"),
                "is_bot": user.get("is_bot"),
                "updated": user.get("updated"),
                "is_app_user": user.get("is_app_user"),
                "has_2fa": user.get("has_2fa")
            }
            
            return self._create_tool_result(user_info)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get user info: {str(e)}", is_error=True)
    
    async def _handle_upload_file(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle file upload request."""
        required = ["channels", "file", "filename"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            # For file upload, we need to use a different approach
            # Slack file upload requires multipart form data
            
            upload_data = {
                "channels": params["channels"],
                "filename": params["filename"]
            }
            
            if "title" in params:
                upload_data["title"] = params["title"]
            if "initial_comment" in params:
                upload_data["initial_comment"] = params["initial_comment"]
            
            # Add file content as form data
            upload_data["file"] = params["file"]
            
            # Make multipart request
            response = await self._make_multipart_request("files.upload", upload_data)
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            file_info = response.get("file", {})
            
            result = {
                "file_id": file_info.get("id"),
                "name": file_info.get("name"),
                "title": file_info.get("title"),
                "mimetype": file_info.get("mimetype"),
                "filetype": file_info.get("filetype"),
                "size": file_info.get("size"),
                "url_private": file_info.get("url_private"),
                "url_private_download": file_info.get("url_private_download"),
                "permalink": file_info.get("permalink"),
                "permalink_public": file_info.get("permalink_public"),
                "channels": file_info.get("channels", []),
                "groups": file_info.get("groups", []),
                "ims": file_info.get("ims", []),
                "comments_count": file_info.get("comments_count"),
                "created": file_info.get("created"),
                "timestamp": file_info.get("timestamp"),
                "user": file_info.get("user"),
                "user_team": file_info.get("user_team"),
                "editable": file_info.get("editable"),
                "size": file_info.get("size"),
                "mode": file_info.get("mode"),
                "is_external": file_info.get("is_external"),
                "external_type": file_info.get("external_type"),
                "is_public": file_info.get("is_public"),
                "public_url_shared": file_info.get("public_url_shared"),
                "display_as_bot": file_info.get("display_as_bot"),
                "username": file_info.get("username")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to upload file: {str(e)}", is_error=True)
    
    async def _make_multipart_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make multipart request for file uploads."""
        try:
            if not self.session:
                await self.initialize()
            
            # Prepare multipart form data
            import aiohttp
            from aiohttp import FormData
            
            form_data = FormData()
            
            for key, value in data.items():
                if key == "file":
                    # Handle file content
                    form_data.add_field(key, value, filename=data.get("filename", "file"))
                else:
                    form_data.add_field(key, str(value))
            
            # Get auth headers
            auth_headers = await self._get_auth_headers(getattr(self, 'user_id', None))
            
            url = f"{self._get_api_url()}/{endpoint}"
            
            async with self.session.post(url, data=form_data, headers=auth_headers) as response:
                response_text = await response.text()
                
                try:
                    return json.loads(response_text) if response_text else {}
                except json.JSONDecodeError:
                    return {"raw_response": response_text}
                    
        except Exception as e:
            logger.error("Multipart request failed", endpoint=endpoint, error=str(e))
            raise
    
    async def _handle_create_channel(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create channel request."""
        required = ["name"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            channel_data = {
                "name": params["name"]
            }
            
            if "is_private" in params:
                channel_data["is_private"] = str(params["is_private"]).lower()
            
            response = await self.make_request(
                "POST",
                "conversations.create",
                data=channel_data,
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            channel = response.get("channel", {})
            
            result = {
                "id": channel.get("id"),
                "name": channel.get("name"),
                "is_channel": channel.get("is_channel"),
                "is_group": channel.get("is_group"),
                "is_im": channel.get("is_im"),
                "is_mpim": channel.get("is_mpim"),
                "is_private": channel.get("is_private"),
                "is_archived": channel.get("is_archived"),
                "is_general": channel.get("is_general"),
                "created": channel.get("created"),
                "creator": channel.get("creator"),
                "is_archived": channel.get("is_archived"),
                "is_general": channel.get("is_general"),
                "name_normalized": channel.get("name_normalized")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create channel: {str(e)}", is_error=True)
    
    async def _handle_set_channel_topic(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle set channel topic request."""
        required = ["channel", "topic"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request(
                "POST",
                "conversations.setTopic",
                data={
                    "channel": params["channel"],
                    "topic": params["topic"]
                },
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            channel = response.get("channel", {})
            
            result = {
                "id": channel.get("id"),
                "name": channel.get("name"),
                "topic": {
                    "value": channel.get("topic", {}).get("value"),
                    "creator": channel.get("topic", {}).get("creator"),
                    "last_set": channel.get("topic", {}).get("last_set")
                }
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to set channel topic: {str(e)}", is_error=True)
    
    async def _handle_search_messages(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle search messages request."""
        required = ["query"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            query_params = {
                "query": params["query"],
                "count": min(params.get("count", 20), 100),
                "page": params.get("page", 1)
            }
            
            if "sort" in params:
                query_params["sort"] = params["sort"]
            
            response = await self.make_request(
                "GET",
                "search.messages",
                params=query_params,
                user_id=getattr(self, 'user_id', None)
            )
            
            if not response.get("ok"):
                return self._create_tool_result(f"Slack API error: {response.get('error')}", is_error=True)
            
            messages_data = response.get("messages", {})
            messages = []
            
            for message in messages_data.get("matches", []):
                messages.append({
                    "text": message.get("text"),
                    "username": message.get("username"),
                    "channel": {
                        "id": message.get("channel", {}).get("id"),
                        "name": message.get("channel", {}).get("name")
                    },
                    "user": message.get("user"),
                    "ts": message.get("ts"),
                    "permalink": message.get("permalink"),
                    "no_index": message.get("no_index"),
                    "type": message.get("type"),
                    "subtype": message.get("subtype"),
                    "team": message.get("team")
                })
            
            result = {
                "query": query_params["query"],
                "total": messages_data.get("total", 0),
                "pagination": {
                    "first": messages_data.get("first", 0),
                    "last": messages_data.get("last", 0),
                    "total_count": messages_data.get("total_count", 0)
                },
                "messages": messages
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to search messages: {str(e)}", is_error=True)