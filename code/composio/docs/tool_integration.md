# Tool Integration Guide

This guide explains how to integrate external tools and services with the Composio MCP Server.

## Architecture Overview

The tool integration system consists of:

- **Base Tool Handler**: Abstract base class for all tools
- **Tool Implementations**: Specific handlers for each service
- **Authentication Manager**: Handles user credentials
- **Rate Limiter**: Manages request throttling
- **Error Handling**: Consistent error responses

## Available Integrations

### Version Control: GitHub

**Capabilities**:
- Repository management (create, read, update)
- Issue tracking and management
- Pull request creation and management
- Release management
- Gist creation and sharing
- User and organization information

**Authentication**: GitHub Personal Access Token

**Rate Limits**:
- API calls: 5,000 per hour per user
- Search: 30 per minute
- Gists: 60 per hour

**Example Usage**:
```python
# Get repository information
result = await github_tool.call_tool({
    "name": "github_repository_info",
    "arguments": {
        "owner": "microsoft",
        "repo": "vscode"
    }
})

# Create an issue
result = await github_tool.call_tool({
    "name": "github_create_issue",
    "arguments": {
        "owner": "your-org",
        "repo": "your-project",
        "title": "Bug report: Memory leak detected",
        "body": "Description of the issue...",
        "labels": ["bug", "memory"]
    }
})
```

### Communication: Slack

**Capabilities**:
- Send messages to channels and users
- List and manage channels
- User management and information
- File uploads
- Channel management (create, set topics)
- Message search

**Authentication**: Slack Bot Token

**Rate Limits**:
- API calls: 100 per hour
- File uploads: 10 per minute
- Messages: 1 per second per channel

**Example Usage**:
```python
# Send a message
result = await slack_tool.call_tool({
    "name": "slack_send_message",
    "arguments": {
        "channel": "#general",
        "text": "Trading alert: AAPL price exceeded $150",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*AAPL Trading Alert* :chart_with_upwards_trend:\nPrice: $150.25"
                }
            }
        ]
    }
})

# Create a channel
result = await slack_tool.call_tool({
    "name": "slack_create_channel",
    "arguments": {
        "name": "trading-signals",
        "is_private": false
    }
})
```

### Messaging: Telegram

**Capabilities**:
- Send messages to chats and channels
- Get bot and chat information
- Handle bot updates
- Message formatting (HTML/Markdown)

**Authentication**: Telegram Bot Token

**Rate Limits**:
- Messages: 30 per second
- API calls: 30 per minute

**Example Usage**:
```python
# Send a message
result = await telegram_tool.call_tool({
    "name": "telegram_send_message",
    "arguments": {
        "chat_id": "@your_channel",
        "text": "Market Update: NASDAQ reached new high",
        "parse_mode": "HTML"
    }
})
```

### Productivity: Notion

**Capabilities**:
- Create and manage pages and databases
- Search content across workspace
- Block-level content manipulation
- Page properties and metadata

**Authentication**: Notion Integration Token

**Rate Limits**:
- API calls: 100 per minute
- Database queries: 20 per second

**Example Usage**:
```python
# Create a page
result = await notion_tool.call_tool({
    "name": "notion_create_page",
    "arguments": {
        "parent_id": "your-database-id",
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": "Trading Strategy Analysis"
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": "In Progress"
                }
            }
        },
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "text": {
                                "content": "Strategy Performance"
                            }
                        }
                    ]
                }
            }
        ]
    }
})
```

### Trading: QuantConnect

**Capabilities**:
- Algorithm creation and backtesting
- Live trading deployment
- Market data retrieval
- Portfolio optimization
- Risk management analysis

**Authentication**: QuantConnect API Token

**Rate Limits**:
- API calls: 10 per minute
- Backtests: 2 per minute

**Example Usage**:
```python
# Create a trading algorithm
result = await quantconnect_tool.call_tool({
    "name": "quantconnect_create_algorithm",
    "arguments": {
        "name": "Moving Average Crossover",
        "description": "Simple moving average crossover strategy",
        "language": "Python",
        "code": "class MovingAverageCross(QCAlgorithm):\n    def Initialize(self):\n        self.SetStartDate(2020, 1, 1)\n        # Algorithm implementation..."
    }
})

# Run a backtest
result = await quantconnect_tool.call_tool({
    "name": "quantconnect_backtest",
    "arguments": {
        "project_id": "12345",
        "algorithm_id": "67890",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31"
    }
})
```

### AI Analytics: Abacus.AI

**Capabilities**:
- AI model creation and training
- Financial predictions and analysis
- Risk assessment and scenarios
- Market sentiment analysis
- Portfolio optimization with AI
- Monte Carlo simulations

**Authentication**: Abacus.AI API Key

**Rate Limits**:
- API calls: 5 per minute
- Model predictions: 10 per minute

**Example Usage**:
```python
# Create an AI model
result = await abacus_tool.call_tool({
    "name": "abacus_create_model",
    "arguments": {
        "name": "Stock Price Predictor",
        "type": "price_prediction",
        "data_source": {
            "symbol": "AAPL",
            "source": "yahoo_finance",
            "period": "1year"
        },
        "parameters": {
            "model_type": "lstm",
            "sequence_length": 60,
            "epochs": 100
        }
    }
})

# Generate trading signals
result = await abacus_tool.call_tool({
    "name": "abacus_trading_signals",
    "arguments": {
        "symbols": ["AAPL", "GOOGL", "MSFT"],
        "signal_types": ["buy", "sell", "technical"],
        "timeframe": "1D"
    }
})
```

## Custom Tool Development

### Creating a New Tool Handler

1. **Inherit from BaseToolHandler**:

```python
from tools.base import BaseToolHandler

class MyCustomToolHandler(BaseToolHandler):
    def __init__(self, settings, auth_manager, rate_limiter):
        super().__init__(settings, auth_manager, rate_limiter)
        self.name = "my_custom_tool"
    
    async def list_tools(self) -> List[Tool]:
        return [
            Tool(
                name="my_custom_action",
                description="Perform a custom action",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"},
                        "param2": {"type": "number"}
                    },
                    "required": ["param1"]
                }
            )
        ]
    
    async def call_tool(self, request) -> CallToolResult:
        # Implementation here
        pass
```

2. **Register the tool in the server**:
```python
# In composio_server.py
from tools.my_custom_tool import MyCustomToolHandler

handler = MyCustomToolHandler(settings, auth_manager, rate_limiter)
self.tool_handlers[handler.name] = handler
```

### Authentication Patterns

#### API Key Authentication
```python
async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
    credentials = await self.get_user_credentials(user_id)
    if not credentials or "api_key" not in credentials:
        raise AuthenticationError("API key not found")
    
    return {
        "Authorization": f"Bearer {credentials['api_key']}"
    }
```

#### OAuth2 Authentication
```python
async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
    credentials = await self.get_user_credentials(user_id)
    if not credentials or "access_token" not in credentials:
        raise AuthenticationError("Access token not found")
    
    return {
        "Authorization": f"Bearer {credentials['access_token']}"
    }
```

#### Custom Headers
```python
async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
    credentials = await self.get_user_credentials(user_id)
    if not credentials:
        raise AuthenticationError("Credentials not found")
    
    return {
        "X-API-Key": credentials.get("api_key"),
        "X-Client-ID": credentials.get("client_id")
    }
```

### Error Handling

#### Standard Error Response
```python
try:
    response = await self.make_request("GET", "endpoint")
    return self._create_tool_result(response)
except AuthenticationError as e:
    return self._create_tool_result(f"Authentication failed: {str(e)}", is_error=True)
except ToolError as e:
    return self._create_tool_result(f"Tool error: {str(e)}", is_error=True)
except Exception as e:
    logger.error("Tool execution failed", error=str(e))
    return self._create_tool_result(f"Unexpected error: {str(e)}", is_error=True)
```

#### Custom Error Handling
```python
async def _handle_custom_action(self, params: Dict[str, Any]) -> CallToolResult:
    try:
        # Validate parameters
        missing = self._validate_required_params(params, ["param1"])
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        # Business logic
        result = await self._perform_action(params)
        return self._create_tool_result(result)
        
    except CustomException as e:
        return self._create_tool_result(f"Custom error: {str(e)}", is_error=True)
    except Exception as e:
        return self._create_tool_result(f"Internal error: {str(e)}", is_error=True)
```

### Testing Tools

#### Unit Testing
```python
import pytest
from tools.my_custom_tool import MyCustomToolHandler
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_custom_tool():
    # Setup
    settings = MagicMock()
    auth_manager = MagicMock()
    rate_limiter = MagicMock()
    
    tool = MyCustomToolHandler(settings, auth_manager, rate_limiter)
    
    # Mock authentication
    auth_manager.get_tool_credentials.return_value = {"api_key": "test_key"}
    rate_limiter.check_rate_limit.return_value = True
    
    # Test tool listing
    tools = await tool.list_tools()
    assert len(tools) > 0
    assert tools[0].name == "my_custom_action"
    
    # Test tool execution
    request = MagicMock()
    request.params.name = "my_custom_action"
    request.params.arguments = {"param1": "test_value", "param2": 42}
    
    # Mock API response
    tool.make_request = AsyncMock(return_value={"result": "success"})
    
    result = await tool.call_tool(request)
    assert not result.isError
```

#### Integration Testing
```python
@pytest.mark.asyncio
async def test_full_integration():
    # Test the complete workflow
    # This would test the actual server integration
    pass
```

## Best Practices

### 1. Parameter Validation
```python
def _validate_required_params(self, params: Dict[str, Any], required: List[str]) -> List[str]:
    missing = []
    for param in required:
        if param not in params or not params[param]:
            missing.append(param)
    return missing
```

### 2. Rate Limiting
```python
async def _handle_rate_limiting(self, request, tool_name: str):
    user_id = getattr(request, 'user_id', None)
    await super()._handle_rate_limiting(user_id, tool_name)
```

### 3. Response Formatting
```python
def _create_tool_result(self, content: Any, is_error: bool = False) -> CallToolResult:
    if isinstance(content, dict):
        content_text = json.dumps(content, indent=2)
    else:
        content_text = str(content)
    
    return CallToolResult(
        content=[{"type": "text", "text": content_text}],
        isError=is_error
    )
```

### 4. Logging
```python
logger = structlog.get_logger()

# In methods
logger.info("Action performed", param1=param1, param2=param2)
logger.error("Action failed", error=str(error))
```

### 5. Async Patterns
```python
# Always use async/await
async def call_tool(self, request) -> CallToolResult:
    try:
        await self.initialize()  # Ensure initialization
        
        # Use async calls
        result = await self.make_async_request()
        
        return self._create_tool_result(result)
    finally:
        await self.cleanup()  # Proper cleanup
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check token format and validity
   - Verify token permissions
   - Ensure token hasn't expired

2. **Rate Limit Errors**
   - Check rate limit configuration
   - Implement exponential backoff
   - Monitor usage patterns

3. **Timeout Issues**
   - Increase timeout settings
   - Check network connectivity
   - Optimize API calls

4. **Response Parsing**
   - Validate API response format
   - Handle optional fields gracefully
   - Add logging for debugging

### Debug Mode
Enable detailed logging:
```json
{
  "logging": {
    "level": "DEBUG",
    "format": "json"
  }
}
```

### Health Checks
Monitor tool health:
```python
async def test_connection(self) -> bool:
    try:
        response = await self.make_request("GET", "health")
        return response.get("status") == "ok"
    except Exception:
        return False
```

## Security Considerations

### 1. Credential Management
- Store credentials encrypted
- Use principle of least privilege
- Regular credential rotation

### 2. Input Validation
- Validate all parameters
- Sanitize user inputs
- Use parameterized queries

### 3. Error Handling
- Don't expose sensitive information
- Log errors securely
- Provide generic error messages

### 4. Rate Limiting
- Implement per-user limits
- Use sliding window counters
- Monitor for abuse patterns

## Performance Optimization

### 1. Connection Pooling
```python
# Reuse HTTP sessions
async def initialize(self):
    if not self.session:
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
```

### 2. Caching
```python
# Cache frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=128)
async def get_cached_data(self, key: str):
    # Implementation here
    pass
```

### 3. Batch Operations
```python
# Batch multiple requests when possible
async def batch_requests(self, requests: List[Dict]) -> List[Dict]:
    # Use connection pooling for batch operations
    # Process requests concurrently
    # Handle partial failures gracefully
    pass
```

This integration guide provides comprehensive information for developing, deploying, and maintaining tool integrations in the Composio MCP Server.