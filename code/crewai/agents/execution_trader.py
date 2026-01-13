"""
Execution Trader Agent
Responsible for optimal trade execution and order management
"""
from typing import Dict, List, Optional, Any, Tuple
from crewai import Agent
from crewai_tools import BaseTool
from utils.memory_manager import memory_manager
from cache.cache_manager import cache_manager
from config.settings import settings, AgentPrompts
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time


class OrderExecutionTool(BaseTool):
    """Tool for optimal order execution strategies"""
    name: str = "Order Execution Tool"
    description: str = "Executes orders using optimal strategies to minimize market impact"
    
    def _run(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order using optimal strategy"""
        try:
            symbol = order_request.get("symbol")
            side = order_request.get("side")  # 'buy' or 'sell'
            quantity = order_request.get("quantity")
            order_type = order_request.get("order_type", "market")
            execution_strategy = order_request.get("execution_strategy", "immediate")
            
            if not all([symbol, side, quantity]):
                return {"error": "Missing required order parameters"}
            
            # Get current market data
            ticker = yf.Ticker(symbol)
            current_data = ticker.history(period="1d")
            
            if current_data.empty:
                return {"error": f"No market data available for {symbol}"}
            
            current_price = float(current_data['Close'].iloc[-1])
            volume = int(current_data['Volume'].iloc[-1])
            bid = float(current_data['Low'].iloc[-1])  # Simplified bid
            ask = float(current_data['High'].iloc[-1])  # Simplified ask
            spread = ask - bid
            
            # Calculate market impact estimates
            avg_daily_volume = volume
            order_size_ratio = quantity / avg_daily_volume if avg_daily_volume > 0 else 0
            
            # Market impact function (simplified)
            if order_size_ratio <= 0.01:  # Less than 1% of daily volume
                market_impact = spread * 0.5  # Half spread
            elif order_size_ratio <= 0.05:  # 1-5% of daily volume
                market_impact = spread + (order_size_ratio * spread * 5)
            else:  # More than 5% of daily volume
                market_impact = spread + (order_size_ratio * spread * 10)
            
            # Execute based on strategy
            execution_result = {}
            
            if execution_strategy == "immediate":
                execution_result = self._execute_immediate(order_request, current_price, market_impact)
            elif execution_strategy == "twap":
                execution_result = self._execute_twap(order_request, current_price, market_impact)
            elif execution_strategy == "vwap":
                execution_result = self._execute_vwap(order_request, current_price, market_impact)
            elif execution_strategy == "iceberg":
                execution_result = self._execute_iceberg(order_request, current_price, market_impact)
            else:
                return {"error": f"Unsupported execution strategy: {execution_strategy}"}
            
            # Add market data to execution result
            execution_result.update({
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "execution_strategy": execution_strategy,
                "current_price": current_price,
                "avg_daily_volume": avg_daily_volume,
                "order_size_ratio": order_size_ratio,
                "estimated_market_impact": market_impact,
                "spread": spread,
                "bid": bid,
                "ask": ask,
                "timestamp": datetime.now().isoformat()
            })
            
            return execution_result
            
        except Exception as e:
            logging.error(f"Error executing order: {e}")
            return {"error": f"Order execution error: {e}"}
    
    def _execute_immediate(self, order_request: Dict[str, Any], current_price: float, market_impact: float) -> Dict[str, Any]:
        """Execute order immediately at current market price"""
        try:
            side = order_request.get("side")
            quantity = order_request.get("quantity")
            
            if side == "buy":
                execution_price = current_price + market_impact
            else:  # sell
                execution_price = current_price - market_impact
            
            total_value = execution_price * quantity
            fees = self._calculate_fees(total_value)
            
            return {
                "strategy": "immediate",
                "execution_price": execution_price,
                "total_value": total_value,
                "fees": fees,
                "slippage": market_impact,
                "execution_time": "immediate",
                "filled_quantity": quantity
            }
            
        except Exception as e:
            return {"error": f"Immediate execution error: {e}"}
    
    def _execute_twap(self, order_request: Dict[str, Any], current_price: float, market_impact: float) -> Dict[str, Any]:
        """Execute order using Time-Weighted Average Price strategy"""
        try:
            side = order_request.get("side")
            quantity = order_request.get("quantity")
            time_horizon = order_request.get("time_horizon", 60)  # minutes
            
            # Split order into smaller chunks
            num_slices = min(10, time_horizon // 5)  # At least 5-minute intervals
            slice_quantity = quantity // num_slices
            remaining_quantity = quantity % num_slices
            
            # Simulate execution over time horizon
            executions = []
            total_cost = 0
            total_fees = 0
            
            for i in range(num_slices):
                slice_price_variance = np.random.normal(0, market_impact * 0.3)  # Price variation
                slice_quantity_adjusted = slice_quantity + (1 if i < remaining_quantity else 0)
                
                if side == "buy":
                    execution_price = current_price + market_impact + slice_price_variance
                else:
                    execution_price = current_price - market_impact + slice_price_variance
                
                slice_cost = execution_price * slice_quantity_adjusted
                slice_fees = self._calculate_fees(slice_cost)
                
                executions.append({
                    "slice": i + 1,
                    "quantity": slice_quantity_adjusted,
                    "execution_price": execution_price,
                    "cost": slice_cost,
                    "fees": slice_fees,
                    "estimated_time": f"+{((i + 1) * time_horizon // num_slices)} minutes"
                })
                
                total_cost += slice_cost
                total_fees += slice_fees
            
            avg_price = total_cost / quantity if quantity > 0 else 0
            
            return {
                "strategy": "twap",
                "executions": executions,
                "total_quantity": quantity,
                "average_price": avg_price,
                "total_cost": total_cost,
                "total_fees": total_fees,
                "time_horizon": time_horizon,
                "expected_slippage": market_impact * 0.6  # TWAP typically has lower impact
            }
            
        except Exception as e:
            return {"error": f"TWAP execution error: {e}"}
    
    def _execute_vwap(self, order_request: Dict[str, Any], current_price: float, market_impact: float) -> Dict[str, Any]:
        """Execute order using Volume-Weighted Average Price strategy"""
        try:
            side = order_request.get("side")
            quantity = order_request.get("quantity")
            
            # Get historical intraday volume pattern
            ticker = yf.Ticker(order_request.get("symbol"))
            
            # Simulate VWAP execution (in real implementation, would use actual volume data)
            # For demo purposes, assume volume is highest at market open and close
            volume_distribution = [0.15, 0.20, 0.15, 0.15, 0.20, 0.15]  # 6 time periods
            
            executions = []
            total_cost = 0
            total_fees = 0
            
            for i, volume_weight in enumerate(volume_distribution):
                slice_quantity = int(quantity * volume_weight)
                if slice_quantity == 0:
                    continue
                
                # Price varies based on volume pattern (higher volume = lower impact)
                price_impact_reduction = volume_weight * market_impact * 2
                slice_price_variance = np.random.normal(0, (market_impact - price_impact_reduction) * 0.5)
                
                if side == "buy":
                    execution_price = current_price + (market_impact - price_impact_reduction) + slice_price_variance
                else:
                    execution_price = current_price - (market_impact - price_impact_reduction) + slice_price_variance
                
                slice_cost = execution_price * slice_quantity
                slice_fees = self._calculate_fees(slice_cost)
                
                executions.append({
                    "period": i + 1,
                    "quantity": slice_quantity,
                    "execution_price": execution_price,
                    "cost": slice_cost,
                    "fees": slice_fees,
                    "volume_weight": volume_weight
                })
                
                total_cost += slice_cost
                total_fees += slice_fees
            
            avg_price = total_cost / quantity if quantity > 0 else 0
            
            return {
                "strategy": "vwap",
                "executions": executions,
                "total_quantity": quantity,
                "average_price": avg_price,
                "total_cost": total_cost,
                "total_fees": total_fees,
                "expected_slippage": market_impact * 0.4  # VWAP typically has lowest impact
            }
            
        except Exception as e:
            return {"error": f"VWAP execution error: {e}"}
    
    def _execute_iceberg(self, order_request: Dict[str, Any], current_price: float, market_impact: float) -> Dict[str, Any]:
        """Execute order using Iceberg strategy to hide order size"""
        try:
            side = order_request.get("side")
            quantity = order_request.get("quantity")
            iceberg_size = order_request.get("iceberg_size", quantity // 10)  # Default to 10% of total
            
            # Execute in small chunks to hide total order size
            executions = []
            total_cost = 0
            total_fees = 0
            remaining_quantity = quantity
            
            while remaining_quantity > 0:
                current_slice = min(iceberg_size, remaining_quantity)
                
                # Iceberg has minimal market impact since size is hidden
                slice_price_variance = np.random.normal(0, market_impact * 0.2)
                
                if side == "buy":
                    execution_price = current_price + market_impact * 0.3 + slice_price_variance
                else:
                    execution_price = current_price - market_impact * 0.3 + slice_price_variance
                
                slice_cost = execution_price * current_slice
                slice_fees = self._calculate_fees(slice_cost)
                
                executions.append({
                    "slice": len(executions) + 1,
                    "quantity": current_slice,
                    "execution_price": execution_price,
                    "cost": slice_cost,
                    "fees": slice_fees
                })
                
                total_cost += slice_cost
                total_fees += slice_fees
                remaining_quantity -= current_slice
                
                # Add random delay between slices (simulate market timing)
                if remaining_quantity > 0:
                    executions[-1]["delay_seconds"] = np.random.randint(30, 300)  # 30s to 5min
            
            avg_price = total_cost / quantity if quantity > 0 else 0
            
            return {
                "strategy": "iceberg",
                "executions": executions,
                "total_quantity": quantity,
                "average_price": avg_price,
                "total_cost": total_cost,
                "total_fees": total_fees,
                "iceberg_size": iceberg_size,
                "expected_slippage": market_impact * 0.5  # Iceberg has moderate impact
            }
            
        except Exception as e:
            return {"error": f"Iceberg execution error: {e}"}
    
    def _calculate_fees(self, trade_value: float) -> float:
        """Calculate trading fees (simplified)"""
        # Simplified fee structure
        base_fee = 0.005  # $0.005 per share (minimum)
        percentage_fee = trade_value * 0.0001  # 0.01% of trade value
        
        return base_fee + percentage_fee


class MarketMonitoringTool(BaseTool):
    """Tool for real-time market monitoring"""
    name: str = "Market Monitoring Tool"
    description: str = "Monitors market conditions and alerts on important events"
    
    def _run(self, monitoring_request: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor market conditions for symbols"""
        try:
            symbols = monitoring_request.get("symbols", [])
            monitoring_type = monitoring_request.get("type", "price_alerts")
            
            if not symbols:
                return {"error": "No symbols provided for monitoring"}
            
            monitoring_results = {}
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="2d")
                    
                    if data.empty:
                        monitoring_results[symbol] = {"error": f"No data for {symbol}"}
                        continue
                    
                    current_price = float(data['Close'].iloc[-1])
                    previous_price = float(data['Close'].iloc[-2])
                    price_change = current_price - previous_price
                    price_change_pct = (price_change / previous_price) * 100
                    
                    volume = int(data['Volume'].iloc[-1])
                    high = float(data['High'].iloc[-1])
                    low = float(data['Low'].iloc[-1])
                    
                    # Calculate technical indicators
                    sma_20 = data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else current_price
                    rsi = self._calculate_rsi(data['Close'].values)
                    
                    monitoring_results[symbol] = {
                        "current_price": current_price,
                        "previous_price": previous_price,
                        "price_change": price_change,
                        "price_change_pct": price_change_pct,
                        "volume": volume,
                        "high": high,
                        "low": low,
                        "sma_20": float(sma_20),
                        "rsi": float(rsi) if rsi else None,
                        "alerts": self._generate_alerts(symbol, current_price, price_change_pct, rsi, volume),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    monitoring_results[symbol] = {"error": str(e)}
            
            return {
                "monitoring_type": monitoring_type,
                "symbols": symbols,
                "results": monitoring_results,
                "summary": self._generate_monitoring_summary(monitoring_results)
            }
            
        except Exception as e:
            return {"error": f"Market monitoring error: {e}"}
    
    def _calculate_rsi(self, prices: np.ndarray, window: int = 14) -> Optional[float]:
        """Calculate RSI indicator"""
        try:
            if len(prices) < window + 1:
                return None
            
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-window:])
            avg_loss = np.mean(losses[-window:])
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except:
            return None
    
    def _generate_alerts(self, symbol: str, price: float, change_pct: float, rsi: Optional[float], volume: int) -> List[Dict[str, Any]]:
        """Generate alerts based on market conditions"""
        alerts = []
        
        # Price change alert
        if abs(change_pct) >= 5:
            alerts.append({
                "type": "price_move",
                "severity": "high" if abs(change_pct) >= 10 else "medium",
                "message": f"{symbol} moved {change_pct:.2f}% to ${price:.2f}",
                "threshold": 5.0
            })
        
        # Volume alert
        if volume > 2000000:  # High volume threshold
            alerts.append({
                "type": "high_volume",
                "severity": "medium",
                "message": f"{symbol} trading at unusually high volume: {volume:,}",
                "volume": volume
            })
        
        # RSI alerts
        if rsi is not None:
            if rsi >= 70:
                alerts.append({
                    "type": "overbought",
                    "severity": "medium",
                    "message": f"{symbol} RSI overbought at {rsi:.1f}",
                    "rsi": rsi
                })
            elif rsi <= 30:
                alerts.append({
                    "type": "oversold",
                    "severity": "medium",
                    "message": f"{symbol} RSI oversold at {rsi:.1f}",
                    "rsi": rsi
                })
        
        return alerts
    
    def _generate_monitoring_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of monitoring results"""
        try:
            total_symbols = len(results)
            symbols_with_errors = sum(1 for r in results.values() if "error" in r)
            symbols_with_alerts = sum(1 for r in results.values() if r.get("alerts"))
            
            all_changes = []
            for r in results.values():
                if "price_change_pct" in r:
                    all_changes.append(r["price_change_pct"])
            
            avg_change = np.mean(all_changes) if all_changes else 0
            max_gain = np.max(all_changes) if all_changes else 0
            max_loss = np.min(all_changes) if all_changes else 0
            
            return {
                "total_symbols": total_symbols,
                "symbols_with_errors": symbols_with_errors,
                "symbols_with_alerts": symbols_with_alerts,
                "average_change_pct": float(avg_change),
                "max_gain_pct": float(max_gain),
                "max_loss_pct": float(max_loss),
                "monitoring_status": "active"
            }
        except Exception as e:
            return {"error": f"Summary generation error: {e}"}


class ExecutionTrader:
    """Execution Trader Agent"""
    
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.logger = logging.getLogger(__name__)
        
        # Create tools
        self.tools = [
            OrderExecutionTool(),
            MarketMonitoringTool()
        ]
        
        # Create agent
        self.agent = Agent(
            role="Execution Trader",
            goal="Execute trades with optimal timing and minimal market impact while managing order flow",
            backstory="""You are an experienced execution trader with expertise in algorithmic trading, market microstructure, 
                        and optimal execution strategies. You understand how to minimize slippage, manage market impact, 
                        and timing trades for maximum efficiency.""",
            tools=self.tools,
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True,
            cache=True,
            llm_config={
                "model": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 2000
            }
        )
    
    async def execute_trade(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trade with optimal strategy"""
        try:
            # Validate trade request
            validation_result = self._validate_trade_request(trade_request)
            if validation_result["valid"] == False:
                return {"error": f"Invalid trade request: {validation_result['errors']}"}
            
            # Execute trade using appropriate strategy
            execution_result = self.tools[0]._run(trade_request)
            
            if "error" not in execution_result:
                # Store execution history
                await memory_manager.store_crew_memory(
                    self.crew_id,
                    f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    execution_result
                )
                
                # Update portfolio state
                await self._update_portfolio_state(trade_request, execution_result)
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return {"error": str(e)}
    
    async def monitor_market_conditions(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Monitor market conditions for optimal execution timing"""
        if not symbols:
            # Default to major indices for market context
            symbols = ["^GSPC", "^DJI", "^IXIC"]
        
        try:
            monitoring_request = {
                "symbols": symbols,
                "type": "execution_timing"
            }
            
            monitoring_result = self.tools[1]._run(monitoring_request)
            
            # Store monitoring results
            await memory_manager.store_agent_memory(
                self.crew_id,
                "execution_trader",
                f"market_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                monitoring_result
            )
            
            return monitoring_result
            
        except Exception as e:
            self.logger.error(f"Error monitoring market: {e}")
            return {"error": str(e)}
    
    async def get_optimal_execution_strategy(self, order_characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal execution strategy based on order characteristics"""
        try:
            symbol = order_characteristics.get("symbol")
            quantity = order_characteristics.get("quantity", 0)
            urgency = order_characteristics.get("urgency", "normal")  # 'low', 'normal', 'high'
            market_conditions = order_characteristics.get("market_conditions", "normal")
            
            # Get current market data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            
            if data.empty:
                return {"error": f"No market data for {symbol}"}
            
            volume = int(data['Volume'].iloc[-1])
            current_price = float(data['Close'].iloc[-1])
            
            # Calculate order size as percentage of daily volume
            order_size_ratio = quantity / volume if volume > 0 else float('inf')
            
            # Decision logic for execution strategy
            strategy_recommendation = {}
            
            if urgency == "high" or order_size_ratio > 0.10:  # High urgency or very large order
                strategy = "iceberg"
                rationale = "High urgency or large order size - use iceberg to minimize market impact"
            elif order_size_ratio > 0.05:  # Large order
                strategy = "twap"
                rationale = "Large order - use TWAP to spread execution over time"
            elif market_conditions == "volatile":
                strategy = "vwap"
                rationale = "Volatile market - use VWAP to match market volume patterns"
            elif urgency == "low":
                strategy = "vwap"
                rationale = "Low urgency - use VWAP for optimal average price"
            else:
                strategy = "immediate"
                rationale = "Normal conditions - immediate execution sufficient"
            
            # Additional recommendations
            recommendations = []
            
            if order_size_ratio > 0.15:
                recommendations.append("Consider breaking order into smaller chunks")
            
            if volume < 1000000:
                recommendations.append("Low liquidity - consider wider time horizon")
            
            if market_conditions == "volatile":
                recommendations.append("Execute during lower volatility periods")
            
            strategy_recommendation = {
                "recommended_strategy": strategy,
                "rationale": rationale,
                "order_size_ratio": order_size_ratio,
                "liquidity_assessment": "high" if volume > 5000000 else "medium" if volume > 1000000 else "low",
                "execution_timeline": self._get_execution_timeline(strategy, urgency),
                "expected_impact": self._estimate_market_impact(order_size_ratio, strategy),
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
            return strategy_recommendation
            
        except Exception as e:
            self.logger.error(f"Error determining execution strategy: {e}")
            return {"error": str(e)}
    
    async def get_execution_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get execution history for analysis"""
        try:
            # Get crew memory to retrieve execution history
            memory_data = await memory_manager.get_crew_memory(self.crew_id)
            
            if not memory_data:
                return {"executions": [], "message": "No execution history found"}
            
            # Extract execution records
            executions = []
            for key, value in memory_data.items():
                if key.startswith("execution_") and isinstance(value, dict):
                    executions.append(value)
            
            # Sort by timestamp and limit results
            executions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            executions = executions[:limit]
            
            # Calculate statistics
            total_executions = len(executions)
            total_value = sum(ex.get("total_value", 0) for ex in executions)
            avg_slippage = np.mean([ex.get("slippage", 0) for ex in executions if "slippage" in ex])
            
            strategy_breakdown = {}
            for execution in executions:
                strategy = execution.get("strategy", "unknown")
                strategy_breakdown[strategy] = strategy_breakdown.get(strategy, 0) + 1
            
            return {
                "executions": executions,
                "statistics": {
                    "total_executions": total_executions,
                    "total_value": total_value,
                    "average_slippage": float(avg_slippage) if total_executions > 0 else 0,
                    "strategy_breakdown": strategy_breakdown
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting execution history: {e}")
            return {"error": str(e)}
    
    def _validate_trade_request(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trade request parameters"""
        required_fields = ["symbol", "side", "quantity"]
        errors = []
        
        # Check required fields
        for field in required_fields:
            if field not in trade_request or not trade_request[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate side
        if "side" in trade_request and trade_request["side"] not in ["buy", "sell"]:
            errors.append("Side must be 'buy' or 'sell'")
        
        # Validate quantity
        if "quantity" in trade_request:
            try:
                quantity = float(trade_request["quantity"])
                if quantity <= 0:
                    errors.append("Quantity must be positive")
            except (ValueError, TypeError):
                errors.append("Quantity must be a valid number")
        
        # Validate execution strategy
        valid_strategies = ["immediate", "twap", "vwap", "iceberg"]
        if "execution_strategy" in trade_request:
            strategy = trade_request["execution_strategy"]
            if strategy not in valid_strategies:
                errors.append(f"Invalid execution strategy. Must be one of: {valid_strategies}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _update_portfolio_state(self, trade_request: Dict[str, Any], execution_result: Dict[str, Any]):
        """Update portfolio state after trade execution"""
        try:
            # Get current portfolio state
            portfolio_state = await memory_manager.get_portfolio_state(self.crew_id)
            
            if not portfolio_state:
                portfolio_state = {
                    "positions": {},
                    "cash": 100000,  # Starting cash
                    "total_value": 100000
                }
            
            symbol = trade_request["symbol"]
            side = trade_request["side"]
            quantity = float(trade_request["quantity"])
            execution_price = execution_result.get("execution_price", 0)
            
            # Update position
            current_position = portfolio_state["positions"].get(symbol, {"quantity": 0, "avg_price": 0})
            
            if side == "buy":
                new_quantity = current_position["quantity"] + quantity
                new_avg_price = ((current_position["quantity"] * current_position["avg_price"]) + 
                               (quantity * execution_price)) / new_quantity if new_quantity > 0 else 0
            else:  # sell
                new_quantity = current_position["quantity"] - quantity
                new_avg_price = current_position["avg_price"]
            
            portfolio_state["positions"][symbol] = {
                "quantity": new_quantity,
                "avg_price": new_avg_price
            }
            
            # Update cash
            if side == "buy":
                portfolio_state["cash"] -= quantity * execution_price
            else:
                portfolio_state["cash"] += quantity * execution_price
            
            # Update total value (simplified)
            portfolio_state["total_value"] = portfolio_state["cash"]  # Would need current prices for full calculation
            
            # Store updated state
            await memory_manager.store_portfolio_state(self.crew_id, portfolio_state)
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio state: {e}")
    
    def _get_execution_timeline(self, strategy: str, urgency: str) -> str:
        """Get expected execution timeline"""
        if strategy == "immediate":
            return "Seconds"
        elif strategy == "twap":
            return f"{(60 if urgency == 'high' else 180)} minutes"
        elif strategy == "vwap":
            return f"{(120 if urgency == 'high' else 360)} minutes"
        elif strategy == "iceberg":
            return f"{(90 if urgency == 'high' else 240)} minutes"
        else:
            return "Variable"
    
    def _estimate_market_impact(self, order_size_ratio: float, strategy: str) -> str:
        """Estimate expected market impact"""
        impact_multipliers = {
            "immediate": 1.0,
            "twap": 0.6,
            "vwap": 0.4,
            "iceberg": 0.5
        }
        
        base_impact = min(order_size_ratio * 10, 1.0)  # Base impact proportional to order size
        strategy_multiplier = impact_multipliers.get(strategy, 1.0)
        estimated_impact = base_impact * strategy_multiplier
        
        if estimated_impact <= 0.1:
            return "Low"
        elif estimated_impact <= 0.3:
            return "Medium"
        else:
            return "High"
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance"""
        return self.agent


# Example usage function
async def create_execution_trader(crew_id: str) -> ExecutionTrader:
    """Factory function to create Execution Trader"""
    trader = ExecutionTrader(crew_id)
    
    # Initialize memory connections
    await memory_manager.connect()
    
    return trader