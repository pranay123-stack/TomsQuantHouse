"""
GitHub tool handler for Composio MCP Server.
"""

import json
import re
from typing import Any, Dict, List, Optional

import structlog
from mcp.server.models import Tool
from mcp.types import CallToolResult

from .base import BaseToolHandler, AuthenticationError, ToolError

logger = structlog.get_logger()


class GitHubToolHandler(BaseToolHandler):
    """GitHub API tool handler."""
    
    def __init__(self, settings, auth_manager, rate_limiter):
        super().__init__(settings, auth_manager, rate_limiter)
        self.github_config = settings.tools.github
        
        # Rate limit tracking
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
    
    def _get_test_endpoint(self) -> str:
        """GitHub API test endpoint."""
        return "https://api.github.com/rate_limit"
    
    def _get_items_key(self) -> str:
        """Items key in GitHub API responses."""
        return "items"
    
    async def list_tools(self) -> List[Tool]:
        """List available GitHub tools."""
        return [
            Tool(
                name="github_repository_info",
                description="Get information about a GitHub repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner (username or organization)"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            Tool(
                name="github_create_issue",
                description="Create a new issue in a GitHub repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title"
                        },
                        "body": {
                            "type": "string",
                            "description": "Issue body content"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to add to the issue"
                        }
                    },
                    "required": ["owner", "repo", "title"]
                }
            ),
            Tool(
                name="github_list_issues",
                description="List issues in a GitHub repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "Issue state filter",
                            "default": "open"
                        },
                        "labels": {
                            "type": "string",
                            "description": "Label filter (comma-separated)"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["created", "updated", "comments"],
                            "description": "Sort criteria",
                            "default": "created"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            Tool(
                name="github_create_pull_request",
                description="Create a new pull request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "title": {
                            "type": "string",
                            "description": "Pull request title"
                        },
                        "body": {
                            "type": "string",
                            "description": "Pull request description"
                        },
                        "head": {
                            "type": "string",
                            "description": "Head branch (source)"
                        },
                        "base": {
                            "type": "string",
                            "description": "Base branch (target)",
                            "default": "main"
                        }
                    },
                    "required": ["owner", "repo", "title", "head"]
                }
            ),
            Tool(
                name="github_list_releases",
                description="List releases for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Number of releases per page",
                            "default": 30,
                            "maximum": 100
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            Tool(
                name="github_get_user_info",
                description="Get GitHub user information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username"
                        }
                    },
                    "required": ["username"]
                }
            ),
            Tool(
                name="github_create_gist",
                description="Create a new GitHub Gist",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Gist description"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Filename for the gist"
                        },
                        "content": {
                            "type": "string",
                            "description": "File content"
                        },
                        "public": {
                            "type": "boolean",
                            "description": "Whether the gist should be public",
                            "default": False
                        }
                    },
                    "required": ["filename", "content"]
                }
            ),
            Tool(
                name="github_search_repositories",
                description="Search GitHub repositories",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (GitHub search syntax)"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["stars", "forks", "help", "updated"],
                            "description": "Sort criteria"
                        },
                        "order": {
                            "type": "string",
                            "enum": ["desc", "asc"],
                            "description": "Sort order",
                            "default": "desc"
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Results per page",
                            "default": 30,
                            "maximum": 100
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    
    def _get_tool_permissions(self) -> Dict[str, List[str]]:
        """Get required permissions for each GitHub tool."""
        return {
            "github_repository_info": ["read"],
            "github_create_issue": ["write"],
            "github_list_issues": ["read"],
            "github_create_pull_request": ["write"],
            "github_list_releases": ["read"],
            "github_get_user_info": ["read"],
            "github_create_gist": ["write"],
            "github_search_repositories": ["read"]
        }
    
    async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """Get GitHub authentication headers."""
        if not user_id:
            return {}
        
        credentials = await self.get_user_credentials(user_id)
        if not credentials or "token" not in credentials:
            raise AuthenticationError("GitHub token not found in user credentials")
        
        return {
            "Authorization": f"token {credentials['token']}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def call_tool(self, request) -> CallToolResult:
        """Handle GitHub tool execution."""
        tool_name = request.params.name
        params = request.params.arguments or {}
        
        try:
            # Handle rate limiting
            await self._handle_rate_limiting(request, tool_name)
            
            # Route to appropriate handler
            if tool_name == "github_repository_info":
                return await self._handle_repository_info(params)
            elif tool_name == "github_create_issue":
                return await self._handle_create_issue(params)
            elif tool_name == "github_list_issues":
                return await self._handle_list_issues(params)
            elif tool_name == "github_create_pull_request":
                return await self._handle_create_pull_request(params)
            elif tool_name == "github_list_releases":
                return await self._handle_list_releases(params)
            elif tool_name == "github_get_user_info":
                return await self._handle_get_user_info(params)
            elif tool_name == "github_create_gist":
                return await self._handle_create_gist(params)
            elif tool_name == "github_search_repositories":
                return await self._handle_search_repositories(params)
            else:
                return self._create_tool_result(f"Unknown GitHub tool: {tool_name}", is_error=True)
                
        except AuthenticationError as e:
            logger.error("GitHub authentication error", error=str(e))
            return self._create_tool_result(f"Authentication failed: {str(e)}", is_error=True)
        except Exception as e:
            logger.error("GitHub tool execution failed", tool=tool_name, error=str(e))
            return self._create_tool_result(f"Tool execution failed: {str(e)}", is_error=True)
    
    async def _handle_rate_limiting(self, request, tool_name: str):
        """Handle rate limiting for GitHub requests."""
        # Get user from request context
        user_id = getattr(request, 'user_id', None)
        await super()._handle_rate_limiting(user_id, tool_name)
        
        # Update rate limit info from response headers
        if hasattr(request, 'response_headers'):
            self._update_rate_limit_info(request.response_headers)
    
    def _update_rate_limit_info(self, headers):
        """Update rate limit information from response headers."""
        try:
            remaining = headers.get('X-RateLimit-Remaining')
            reset_time = headers.get('X-RateLimit-Reset')
            
            if remaining:
                self.rate_limit_remaining = int(remaining)
            if reset_time:
                self.rate_limit_reset = int(reset_time)
                
            logger.debug(
                "GitHub rate limit updated",
                remaining=self.rate_limit_remaining,
                reset=self.rate_limit_reset
            )
        except (ValueError, TypeError):
            pass
    
    async def _handle_repository_info(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle repository information request."""
        # Validate parameters
        required = ["owner", "repo"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request(
                "GET", 
                f"repos/{params['owner']}/{params['repo']}",
                user_id=getattr(self, 'user_id', None)
            )
            
            # Extract relevant information
            repo_info = {
                "name": response.get("name"),
                "full_name": response.get("full_name"),
                "description": response.get("description"),
                "html_url": response.get("html_url"),
                "clone_url": response.get("clone_url"),
                "default_branch": response.get("default_branch"),
                "language": response.get("language"),
                "stars": response.get("stargazers_count"),
                "forks": response.get("forks_count"),
                "open_issues": response.get("open_issues_count"),
                "created_at": response.get("created_at"),
                "updated_at": response.get("updated_at"),
                "pushed_at": response.get("pushed_at"),
                "size": response.get("size"),
                "license": response.get("license", {}).get("name") if response.get("license") else None,
                "archived": response.get("archived"),
                "disabled": response.get("disabled")
            }
            
            return self._create_tool_result(repo_info)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get repository info: {str(e)}", is_error=True)
    
    async def _handle_create_issue(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create issue request."""
        required = ["owner", "repo", "title"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            # Prepare issue data
            issue_data = {
                "title": params["title"],
                "body": params.get("body", ""),
                "labels": params.get("labels", [])
            }
            
            response = await self.make_request(
                "POST",
                f"repos/{params['owner']}/{params['repo']}/issues",
                data=issue_data,
                user_id=getattr(self, 'user_id', None)
            )
            
            result = {
                "issue_number": response.get("number"),
                "url": response.get("html_url"),
                "title": response.get("title"),
                "state": response.get("state"),
                "created_at": response.get("created_at"),
                "author": response.get("user", {}).get("login"),
                "labels": [label.get("name") for label in response.get("labels", [])]
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create issue: {str(e)}", is_error=True)
    
    async def _handle_list_issues(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle list issues request."""
        required = ["owner", "repo"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            query_params = {
                "state": params.get("state", "open"),
                "sort": params.get("sort", "created"),
                "per_page": min(params.get("per_page", 30), 100)
            }
            
            if params.get("labels"):
                query_params["labels"] = params["labels"]
            
            response = await self.make_request(
                "GET",
                f"repos/{params['owner']}/{params['repo']}/issues",
                params=query_params,
                user_id=getattr(self, 'user_id', None)
            )
            
            issues = []
            for issue in response:
                issues.append({
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "state": issue.get("state"),
                    "author": issue.get("user", {}).get("login"),
                    "created_at": issue.get("created_at"),
                    "updated_at": issue.get("updated_at"),
                    "url": issue.get("html_url"),
                    "labels": [label.get("name") for label in issue.get("labels", [])],
                    "comments": issue.get("comments", 0),
                    "assignee": issue.get("assignee", {}).get("login") if issue.get("assignee") else None
                })
            
            return self._create_tool_result({
                "total_count": len(issues),
                "issues": issues
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to list issues: {str(e)}", is_error=True)
    
    async def _handle_create_pull_request(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create pull request request."""
        required = ["owner", "repo", "title", "head"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            pr_data = {
                "title": params["title"],
                "body": params.get("body", ""),
                "head": params["head"],
                "base": params.get("base", "main")
            }
            
            response = await self.make_request(
                "POST",
                f"repos/{params['owner']}/{params['repo']}/pulls",
                data=pr_data,
                user_id=getattr(self, 'user_id', None)
            )
            
            result = {
                "pr_number": response.get("number"),
                "url": response.get("html_url"),
                "title": response.get("title"),
                "state": response.get("state"),
                "created_at": response.get("created_at"),
                "author": response.get("user", {}).get("login"),
                "head_branch": response.get("head", {}).get("ref"),
                "base_branch": response.get("base", {}).get("ref"),
                "mergeable": response.get("mergeable"),
                "draft": response.get("draft", False)
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create pull request: {str(e)}", is_error=True)
    
    async def _handle_list_releases(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle list releases request."""
        required = ["owner", "repo"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            query_params = {
                "per_page": min(params.get("per_page", 30), 100)
            }
            
            response = await self.make_request(
                "GET",
                f"repos/{params['owner']}/{params['repo']}/releases",
                params=query_params,
                user_id=getattr(self, 'user_id', None)
            )
            
            releases = []
            for release in response:
                releases.append({
                    "tag_name": release.get("tag_name"),
                    "name": release.get("name"),
                    "body": release.get("body"),
                    "html_url": release.get("html_url"),
                    "tarball_url": release.get("tarball_url"),
                    "zipball_url": release.get("zipball_url"),
                    "published_at": release.get("published_at"),
                    "created_at": release.get("created_at"),
                    "prerelease": release.get("prerelease", False),
                    "draft": release.get("draft", False),
                    "author": release.get("author", {}).get("login") if release.get("author") else None,
                    "download_count": release.get("download_count", 0)
                })
            
            return self._create_tool_result({
                "total_count": len(releases),
                "releases": releases
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to list releases: {str(e)}", is_error=True)
    
    async def _handle_get_user_info(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get user info request."""
        required = ["username"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request(
                "GET",
                f"users/{params['username']}",
                user_id=getattr(self, 'user_id', None)
            )
            
            user_info = {
                "username": response.get("login"),
                "name": response.get("name"),
                "bio": response.get("bio"),
                "company": response.get("company"),
                "location": response.get("location"),
                "blog": response.get("blog"),
                "email": response.get("email"),
                "html_url": response.get("html_url"),
                "avatar_url": response.get("avatar_url"),
                "public_repos": response.get("public_repos", 0),
                "public_gists": response.get("public_gists", 0),
                "followers": response.get("followers", 0),
                "following": response.get("following", 0),
                "created_at": response.get("created_at"),
                "updated_at": response.get("updated_at"),
                "hireable": response.get("hireable"),
                "twitter_username": response.get("twitter_username")
            }
            
            return self._create_tool_result(user_info)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get user info: {str(e)}", is_error=True)
    
    async def _handle_create_gist(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create gist request."""
        required = ["filename", "content"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            # Prepare gist files
            files = {
                params["filename"]: {
                    "content": params["content"]
                }
            }
            
            gist_data = {
                "description": params.get("description", ""),
                "public": params.get("public", False),
                "files": files
            }
            
            response = await self.make_request(
                "POST",
                "gists",
                data=gist_data,
                user_id=getattr(self, 'user_id', None)
            )
            
            result = {
                "gist_id": response.get("id"),
                "html_url": response.get("html_url"),
                "git_pull_url": response.get("git_pull_url"),
                "git_push_url": response.get("git_push_url"),
                "clone_url": response.get("clone_url"),
                "description": response.get("description"),
                "public": response.get("public"),
                "created_at": response.get("created_at"),
                "updated_at": response.get("updated_at"),
                "files": list(response.get("files", {}).keys())
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create gist: {str(e)}", is_error=True)
    
    async def _handle_search_repositories(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle search repositories request."""
        required = ["query"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            query_params = {
                "q": params["query"],
                "sort": params.get("sort"),
                "order": params.get("order", "desc"),
                "per_page": min(params.get("per_page", 30), 100)
            }
            
            # Remove None values
            query_params = {k: v for k, v in query_params.items() if v is not None}
            
            response = await self.make_request(
                "GET",
                "search/repositories",
                params=query_params,
                user_id=getattr(self, 'user_id', None)
            )
            
            repositories = []
            for repo in response.get("items", []):
                repositories.append({
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "description": repo.get("description"),
                    "html_url": repo.get("html_url"),
                    "clone_url": repo.get("clone_url"),
                    "language": repo.get("language"),
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "open_issues": repo.get("open_issues_count"),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "pushed_at": repo.get("pushed_at"),
                    "owner": repo.get("owner", {}).get("login") if repo.get("owner") else None,
                    "license": repo.get("license", {}).get("name") if repo.get("license") else None
                })
            
            return self._create_tool_result({
                "total_count": response.get("total_count", 0),
                "incomplete_results": response.get("incomplete_results", False),
                "repositories": repositories
            })
            
        except Exception as e:
            return self._create_tool_result(f"Failed to search repositories: {str(e)}", is_error=True)