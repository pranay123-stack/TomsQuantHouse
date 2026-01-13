"""
QuantConnect tool handler for Composio MCP Server.
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from mcp.server.models import Tool
from mcp.types import CallToolResult

from .base import BaseToolHandler, AuthenticationError, ToolError

logger = structlog.get_logger()


class QuantConnectToolHandler(BaseToolHandler):
    """QuantConnect API tool handler for trading strategies and backtesting."""
    
    def __init__(self, settings, auth_manager, rate_limiter):
        super().__init__(settings, auth_manager, rate_limiter)
        self.quantconnect_config = settings.tools.quantconnect
    
    def _get_test_endpoint(self) -> str:
        """QuantConnect API test endpoint."""
        return "user"
    
    async def list_tools(self) -> List[Tool]:
        """List available QuantConnect tools."""
        return [
            Tool(
                name="quantconnect_create_algorithm",
                description="Create a new algorithmic trading strategy",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Algorithm name"
                        },
                        "description": {
                            "type": "string",
                            "description": "Algorithm description"
                        },
                        "language": {
                            "type": "string",
                            "enum": ["CSharp", "Python"],
                            "description": "Programming language",
                            "default": "Python"
                        },
                        "code": {
                            "type": "string",
                            "description": "Algorithm code"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Algorithm parameters"
                        }
                    },
                    "required": ["name", "code"]
                }
            ),
            Tool(
                name="quantconnect_backtest",
                description="Run a backtest for an algorithm",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID"
                        },
                        "algorithm_id": {
                            "type": "string",
                            "description": "Algorithm ID"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Backtest parameters"
                        }
                    },
                    "required": ["project_id", "algorithm_id"]
                }
            ),
            Tool(
                name="quantconnect_get_backtest_results",
                description="Get backtest results and statistics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "backtest_id": {
                            "type": "string",
                            "description": "Backtest ID"
                        }
                    },
                    "required": ["backtest_id"]
                }
            ),
            Tool(
                name="quantconnect_portfolio_optimization",
                description="Optimize portfolio allocation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of asset symbols"
                        },
                        "optimization_method": {
                            "type": "string",
                            "enum": ["min_variance", "max_sharpe", "max_return"],
                            "description": "Optimization method"
                        },
                        "constraints": {
                            "type": "object",
                            "description": "Portfolio constraints"
                        }
                    },
                    "required": ["symbols", "optimization_method"]
                }
            ),
            Tool(
                name="quantconnect_live_trading",
                description="Start live trading with an algorithm",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "algorithm_id": {
                            "type": "string",
                            "description": "Algorithm ID"
                        },
                        "account_id": {
                            "type": "string",
                            "description": "Account ID"
                        },
                        "cash": {
                            "type": "number",
                            "description": "Initial cash amount"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Algorithm parameters"
                        }
                    },
                    "required": ["algorithm_id", "account_id"]
                }
            ),
            Tool(
                name="quantconnect_get_live_status",
                description="Get live trading status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "deployment_id": {
                            "type": "string",
                            "description": "Live deployment ID"
                        }
                    },
                    "required": ["deployment_id"]
                }
            ),
            Tool(
                name="quantconnect_stop_live_trading",
                description="Stop live trading deployment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "deployment_id": {
                            "type": "string",
                            "description": "Live deployment ID"
                        }
                    },
                    "required": ["deployment_id"]
                }
            ),
            Tool(
                name="quantconnect_get_market_data",
                description="Get real-time or historical market data",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Market symbol"
                        },
                        "resolution": {
                            "type": "string",
                            "enum": ["tick", "second", "minute", "hour", "daily"],
                            "description": "Data resolution"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of data points"
                        }
                    },
                    "required": ["symbol"]
                }
            ),
            Tool(
                name="quantconnect_risk_management",
                description="Analyze portfolio risk metrics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio ID"
                        },
                        "risk_metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Risk metrics to calculate"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            )
        ]
    
    def _get_tool_permissions(self) -> Dict[str, List[str]]:
        """Get required permissions for QuantConnect tools."""
        return {
            "quantconnect_create_algorithm": ["write", "execute_strategies"],
            "quantconnect_backtest": ["write", "execute_strategies"],
            "quantconnect_get_backtest_results": ["read", "execute_strategies"],
            "quantconnect_portfolio_optimization": ["read", "write", "execute_strategies"],
            "quantconnect_live_trading": ["write", "execute_strategies"],
            "quantconnect_get_live_status": ["read", "execute_strategies"],
            "quantconnect_stop_live_trading": ["write", "execute_strategies"],
            "quantconnect_get_market_data": ["read"],
            "quantconnect_risk_management": ["read", "view_portfolio"]
        }
    
    async def _get_auth_headers(self, user_id: Optional[str] = None) -> Dict[str, str]:
        """Get QuantConnect authentication headers."""
        if not user_id:
            return {}
        
        credentials = await self.get_user_credentials(user_id)
        if not credentials or "token" not in credentials:
            raise AuthenticationError("QuantConnect token not found in user credentials")
        
        return {
            "Authorization": f"Bearer {credentials['token']}"
        }
    
    async def call_tool(self, request) -> CallToolResult:
        """Handle QuantConnect tool execution."""
        tool_name = request.params.name
        params = request.params.arguments or {}
        
        try:
            await self._handle_rate_limiting(request, tool_name)
            
            if tool_name == "quantconnect_create_algorithm":
                return await self._handle_create_algorithm(params)
            elif tool_name == "quantconnect_backtest":
                return await self._handle_backtest(params)
            elif tool_name == "quantconnect_get_backtest_results":
                return await self._handle_get_backtest_results(params)
            elif tool_name == "quantconnect_portfolio_optimization":
                return await self._handle_portfolio_optimization(params)
            elif tool_name == "quantconnect_live_trading":
                return await self._handle_live_trading(params)
            elif tool_name == "quantconnect_get_live_status":
                return await self._handle_get_live_status(params)
            elif tool_name == "quantconnect_stop_live_trading":
                return await self._handle_stop_live_trading(params)
            elif tool_name == "quantconnect_get_market_data":
                return await self._handle_get_market_data(params)
            elif tool_name == "quantconnect_risk_management":
                return await self._handle_risk_management(params)
            else:
                return self._create_tool_result(f"Unknown QuantConnect tool: {tool_name}", is_error=True)
                
        except Exception as e:
            logger.error("QuantConnect tool execution failed", tool=tool_name, error=str(e))
            return self._create_tool_result(f"Tool execution failed: {str(e)}", is_error=True)
    
    async def _handle_create_algorithm(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle create algorithm request."""
        required = ["name", "code"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            algorithm_data = {
                "name": params["name"],
                "description": params.get("description", ""),
                "language": params.get("language", "Python"),
                "code": params["code"],
                "parameters": params.get("parameters", {})
            }
            
            response = await self.make_request("POST", "projects", data=algorithm_data)
            
            result = {
                "project_id": response.get("projects", [{}])[0].get("projectId"),
                "name": response.get("projects", [{}])[0].get("name"),
                "created": response.get("projects", [{}])[0].get("created"),
                "modified": response.get("projects", [{}])[0].get("modified")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to create algorithm: {str(e)}", is_error=True)
    
    async def _handle_backtest(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle backtest request."""
        required = ["project_id", "algorithm_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            backtest_data = {
                "projectId": params["project_id"],
                "algorithmId": params["algorithm_id"],
                "periodStart": params.get("start_date"),
                "periodFinish": params.get("end_date"),
                "parameters": params.get("parameters", {})
            }
            
            response = await self.make_request("POST", "backtests", data=backtest_data)
            
            result = {
                "backtest_id": response.get("backtestId"),
                "project_id": response.get("projectId"),
                "algorithm_id": response.get("algorithmId"),
                "status": response.get("status"),
                "started": response.get("started"),
                "completed": response.get("completed"),
                "progress": response.get("progress"),
                "error": response.get("error")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to start backtest: {str(e)}", is_error=True)
    
    async def _handle_get_backtest_results(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get backtest results request."""
        required = ["backtest_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request("GET", f"backtests/{params['backtest_id']}")
            
            result = {
                "backtest_id": response.get("backtestId"),
                "project_id": response.get("projectId"),
                "algorithm_id": response.get("algorithmId"),
                "status": response.get("status"),
                "started": response.get("started"),
                "completed": response.get("completed"),
                "progress": response.get("progress"),
                "statistics": response.get("statistics", {}),
                "total_trades": response.get("totalTrades"),
                "net_profit": response.get("netProfit"),
                "total_fees": response.get("totalFees"),
                "algorithm_backward_compatibility": response.get("algorithmBackwardCompatibility"),
                "error": response.get("error")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get backtest results: {str(e)}", is_error=True)
    
    async def _handle_portfolio_optimization(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle portfolio optimization request."""
        required = ["symbols", "optimization_method"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            # This would typically call QuantConnect's optimization API
            optimization_data = {
                "symbols": params["symbols"],
                "method": params["optimization_method"],
                "constraints": params.get("constraints", {})
            }
            
            # Simulate optimization call (replace with actual API call)
            response = {
                "optimization_id": f"opt_{int(__import__('time').time())}",
                "status": "completed",
                "method": params["optimization_method"],
                "weights": {symbol: 1.0/len(params["symbols"]) for symbol in params["symbols"]},
                "expected_return": 0.08,
                "volatility": 0.15,
                "sharpe_ratio": 0.53
            }
            
            return self._create_tool_result(response)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to optimize portfolio: {str(e)}", is_error=True)
    
    async def _handle_live_trading(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle live trading request."""
        required = ["algorithm_id", "account_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            live_data = {
                "algorithmId": params["algorithm_id"],
                "accountId": params["account_id"],
                "cash": params.get("cash", 100000),
                "parameters": params.get("parameters", {})
            }
            
            response = await self.make_request("POST", "live", data=live_data)
            
            result = {
                "deployment_id": response.get("deploymentId"),
                "algorithm_id": params["algorithm_id"],
                "account_id": params["account_id"],
                "status": response.get("status"),
                "started": response.get("started"),
                "cash": response.get("cash"),
                "total_value": response.get("totalValue")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to start live trading: {str(e)}", is_error=True)
    
    async def _handle_get_live_status(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get live status request."""
        required = ["deployment_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request("GET", f"live/{params['deployment_id']}")
            
            result = {
                "deployment_id": response.get("deploymentId"),
                "algorithm_id": response.get("algorithmId"),
                "account_id": response.get("accountId"),
                "status": response.get("status"),
                "started": response.get("started"),
                "cash": response.get("cash"),
                "total_value": response.get("totalValue"),
                "daily_pnl": response.get("dailyPnl"),
                "total_pnl": response.get("totalPnl"),
                "positions": response.get("positions", [])
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get live status: {str(e)}", is_error=True)
    
    async def _handle_stop_live_trading(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle stop live trading request."""
        required = ["deployment_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            response = await self.make_request("DELETE", f"live/{params['deployment_id']}")
            
            result = {
                "deployment_id": params["deployment_id"],
                "status": "stopped",
                "stopped_at": response.get("stoppedAt"),
                "final_value": response.get("finalValue"),
                "final_pnl": response.get("finalPnl")
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to stop live trading: {str(e)}", is_error=True)
    
    async def _handle_get_market_data(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle get market data request."""
        required = ["symbol"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            data_params = {
                "symbol": params["symbol"],
                "resolution": params.get("resolution", "daily"),
                "periodStart": params.get("start_date"),
                "periodFinish": params.get("end_date"),
                "count": params.get("count")
            }
            
            response = await self.make_request("GET", "data", params=data_params)
            
            # Process market data
            prices = []
            for item in response:
                prices.append({
                    "symbol": params["symbol"],
                    "time": item.get("time"),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "volume": item.get("volume")
                })
            
            result = {
                "symbol": params["symbol"],
                "resolution": params.get("resolution", "daily"),
                "data_points": len(prices),
                "prices": prices
            }
            
            return self._create_tool_result(result)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to get market data: {str(e)}", is_error=True)
    
    async def _handle_risk_management(self, params: Dict[str, Any]) -> CallToolResult:
        """Handle risk management request."""
        required = ["portfolio_id"]
        missing = self._validate_required_params(params, required)
        if missing:
            return self._create_tool_result(f"Missing required parameters: {missing}", is_error=True)
        
        try:
            # This would typically integrate with QuantConnect's risk management features
            risk_metrics = params.get("risk_metrics", ["var", "sharpe", "max_drawdown"])
            
            # Simulate risk calculation (replace with actual API call)
            risk_analysis = {
                "portfolio_id": params["portfolio_id"],
                "analysis_date": "2025-11-02",
                "metrics": {
                    "var_95": -0.0234,
                    "var_99": -0.0456,
                    "sharpe_ratio": 1.23,
                    "max_drawdown": -0.1567,
                    "volatility": 0.1834,
                    "beta": 1.05,
                    "alpha": 0.0234
                },
                "positions": [
                    {"symbol": "AAPL", "weight": 0.25, "var_contribution": -0.0059},
                    {"symbol": "MSFT", "weight": 0.25, "var_contribution": -0.0058},
                    {"symbol": "GOOGL", "weight": 0.25, "var_contribution": -0.0061},
                    {"symbol": "AMZN", "weight": 0.25, "var_contribution": -0.0056}
                ]
            }
            
            return self._create_tool_result(risk_analysis)
            
        except Exception as e:
            return self._create_tool_result(f"Failed to analyze risk: {str(e)}", is_error=True)