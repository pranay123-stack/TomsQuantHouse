"""
Chief Risk Officer Agent
Responsible for risk management and portfolio oversight
"""
from typing import Dict, List, Optional, Any, Tuple
from crewai import Agent
from crewai_tools import BaseTool
from utils.memory_manager import memory_manager
from cache.cache_manager import cache_manager, RiskCache
from config.settings import settings, AgentPrompts
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import math


class RiskCalculationTool(BaseTool):
    """Tool for calculating various risk metrics"""
    name: str = "Risk Calculation Tool"
    description: str = "Calculates portfolio risk metrics including VaR, volatility, correlation"
    
    def _run(self, portfolio_data: Dict[str, Any], metric: str = "var") -> Dict[str, Any]:
        """Calculate risk metrics for portfolio"""
        try:
            if metric == "var":
                return self._calculate_var(portfolio_data)
            elif metric == "volatility":
                return self._calculate_volatility(portfolio_data)
            elif metric == "correlation":
                return self._calculate_correlation(portfolio_data)
            elif metric == "drawdown":
                return self._calculate_drawdown(portfolio_data)
            elif metric == "beta":
                return self._calculate_beta(portfolio_data)
            else:
                return {"error": f"Unsupported metric: {metric}"}
                
        except Exception as e:
            logging.error(f"Error calculating {metric}: {e}")
            return {"error": str(e)}
    
    def _calculate_var(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Value at Risk"""
        try:
            positions = portfolio_data.get("positions", {})
            returns_data = portfolio_data.get("returns_data", [])
            confidence_level = portfolio_data.get("confidence_level", 0.95)
            time_horizon = portfolio_data.get("time_horizon", 1)
            
            if not positions or not returns_data:
                return {"error": "Insufficient portfolio data for VaR calculation"}
            
            # Convert returns data to numpy array
            returns_array = np.array(returns_data)
            
            if len(returns_array) == 0:
                return {"error": "No returns data available"}
            
            # Calculate portfolio metrics
            portfolio_value = sum(abs(pos.get("value", 0)) for pos in positions.values())
            
            if portfolio_value <= 0:
                return {"error": "Invalid portfolio value"}
            
            # Calculate historical VaR
            sorted_returns = np.sort(returns_array)
            var_index = int((1 - confidence_level) * len(sorted_returns))
            historical_var = abs(sorted_returns[var_index]) * portfolio_value
            
            # Calculate parametric VaR (assuming normal distribution)
            mean_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            z_score = self._get_z_score(confidence_level)
            parametric_var = abs(mean_return - z_score * std_return) * portfolio_value * math.sqrt(time_horizon)
            
            # Calculate Expected Shortfall (Conditional VaR)
            tail_returns = sorted_returns[:var_index+1]
            expected_shortfall = abs(np.mean(tail_returns)) * portfolio_value if len(tail_returns) > 0 else 0
            
            return {
                "metric": "var",
                "portfolio_value": portfolio_value,
                "confidence_level": confidence_level,
                "time_horizon": time_horizon,
                "historical_var": float(historical_var),
                "parametric_var": float(parametric_var),
                "expected_shortfall": float(expected_shortfall),
                "mean_return": float(mean_return),
                "volatility": float(std_return),
                "data_points": len(returns_array),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"VaR calculation error: {e}"}
    
    def _calculate_volatility(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio volatility"""
        try:
            returns_data = portfolio_data.get("returns_data", [])
            
            if not returns_data:
                return {"error": "No returns data available"}
            
            returns_array = np.array(returns_data)
            
            # Calculate different volatility measures
            historical_vol = np.std(returns_array)
            annualized_vol = historical_vol * np.sqrt(252)  # Assuming daily data
            
            # Calculate rolling volatility
            window = min(30, len(returns_array) // 4)
            if window > 1:
                rolling_vols = []
                for i in range(window, len(returns_array)):
                    window_returns = returns_array[i-window:i]
                    rolling_vols.append(np.std(window_returns))
                
                avg_rolling_vol = np.mean(rolling_vols)
                max_rolling_vol = np.max(rolling_vols)
                min_rolling_vol = np.min(rolling_vols)
            else:
                avg_rolling_vol = historical_vol
                max_rolling_vol = historical_vol
                min_rolling_vol = historical_vol
            
            return {
                "metric": "volatility",
                "historical_volatility": float(historical_vol),
                "annualized_volatility": float(annualized_vol),
                "average_rolling_volatility": float(avg_rolling_vol),
                "max_rolling_volatility": float(max_rolling_vol),
                "min_rolling_volatility": float(min_rolling_vol),
                "volatility_window": window,
                "data_points": len(returns_array),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Volatility calculation error: {e}"}
    
    def _calculate_correlation(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio correlation matrix"""
        try:
            returns_data = portfolio_data.get("returns_data", {})
            
            if not returns_data:
                return {"error": "No returns data available"}
            
            symbols = list(returns_data.keys())
            
            if len(symbols) < 2:
                return {"error": "Need at least 2 assets for correlation analysis"}
            
            # Create returns matrix
            returns_matrix = []
            for symbol in symbols:
                if symbol in returns_data:
                    returns_matrix.append(returns_data[symbol])
            
            if len(returns_matrix) < 2:
                return {"error": "Insufficient data for correlation calculation"}
            
            returns_df = pd.DataFrame(returns_matrix).T
            returns_df.columns = symbols
            
            # Calculate correlation matrix
            correlation_matrix = returns_df.corr()
            
            # Calculate average correlation
            avg_correlation = correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].mean()
            
            # Find highest and lowest correlations
            corr_values = []
            for i in range(len(symbols)):
                for j in range(i+1, len(symbols)):
                    corr_values.append({
                        "assets": f"{symbols[i]}-{symbols[j]}",
                        "correlation": float(correlation_matrix.iloc[i, j])
                    })
            
            corr_values.sort(key=lambda x: x["correlation"], reverse=True)
            
            return {
                "metric": "correlation",
                "correlation_matrix": correlation_matrix.to_dict(),
                "average_correlation": float(avg_correlation),
                "highest_correlation": corr_values[0] if corr_values else None,
                "lowest_correlation": corr_values[-1] if corr_values else None,
                "all_correlations": corr_values,
                "symbols": symbols,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Correlation calculation error: {e}"}
    
    def _calculate_drawdown(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate maximum drawdown and drawdown periods"""
        try:
            portfolio_values = portfolio_data.get("portfolio_values", [])
            
            if not portfolio_values or len(portfolio_values) < 2:
                return {"error": "Insufficient portfolio value data"}
            
            values = np.array(portfolio_values)
            
            # Calculate running maximum
            peak = np.maximum.accumulate(values)
            
            # Calculate drawdown
            drawdown = (values - peak) / peak
            
            # Find maximum drawdown
            max_drawdown = np.min(drawdown)
            max_dd_index = np.argmin(drawdown)
            
            # Find drawdown periods
            in_drawdown = drawdown < -0.01  # 1% threshold
            drawdown_periods = []
            
            if np.any(in_drawdown):
                # Find continuous periods
                dd_changes = np.diff(np.concatenate(([False], in_drawdown, [False])).astype(int))
                start_indices = np.where(dd_changes == 1)[0]
                end_indices = np.where(dd_changes == -1)[0]
                
                for start, end in zip(start_indices, end_indices):
                    period_drawdown = np.min(drawdown[start:end])
                    period_values = values[start:end]
                    
                    drawdown_periods.append({
                        "start_index": int(start),
                        "end_index": int(end),
                        "start_value": float(period_values[0]),
                        "end_value": float(period_values[-1]),
                        "max_drawdown": float(period_drawdown),
                        "duration": int(end - start)
                    })
            
            # Calculate additional metrics
            avg_drawdown = np.mean(drawdown[drawdown < 0]) if np.any(drawdown < 0) else 0
            current_drawdown = drawdown[-1]
            
            return {
                "metric": "drawdown",
                "max_drawdown": float(max_drawdown),
                "max_drawdown_index": int(max_dd_index),
                "avg_drawdown": float(avg_drawdown),
                "current_drawdown": float(current_drawdown),
                "num_drawdown_periods": len(drawdown_periods),
                "drawdown_periods": drawdown_periods,
                "data_points": len(values),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Drawdown calculation error: {e}"}
    
    def _calculate_beta(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio beta relative to market"""
        try:
            portfolio_returns = portfolio_data.get("portfolio_returns", [])
            market_returns = portfolio_data.get("market_returns", [])
            
            if not portfolio_returns or not market_returns or len(portfolio_returns) != len(market_returns):
                return {"error": "Insufficient portfolio or market returns data"}
            
            portfolio_array = np.array(portfolio_returns)
            market_array = np.array(market_returns)
            
            # Remove NaN values
            valid_mask = ~(np.isnan(portfolio_array) | np.isnan(market_array))
            portfolio_clean = portfolio_array[valid_mask]
            market_clean = market_array[valid_mask]
            
            if len(portfolio_clean) < 30:
                return {"error": "Insufficient data for beta calculation (need at least 30 points)"}
            
            # Calculate beta using linear regression
            covariance = np.cov(portfolio_clean, market_clean)[0, 1]
            market_variance = np.var(market_clean)
            
            if market_variance == 0:
                return {"error": "Market variance is zero, cannot calculate beta"}
            
            beta = covariance / market_variance
            alpha = np.mean(portfolio_clean) - beta * np.mean(market_clean)
            
            # Calculate R-squared
            correlation = np.corrcoef(portfolio_clean, market_clean)[0, 1]
            r_squared = correlation ** 2
            
            return {
                "metric": "beta",
                "beta": float(beta),
                "alpha": float(alpha),
                "correlation": float(correlation),
                "r_squared": float(r_squared),
                "market_variance": float(market_variance),
                "portfolio_variance": float(np.var(portfolio_clean)),
                "data_points": len(portfolio_clean),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Beta calculation error: {e}"}
    
    def _get_z_score(self, confidence_level: float) -> float:
        """Get z-score for confidence level"""
        if confidence_level == 0.90:
            return 1.28
        elif confidence_level == 0.95:
            return 1.645
        elif confidence_level == 0.99:
            return 2.33
        else:
            # Approximate using inverse normal (simplified)
            if confidence_level <= 0.5:
                return -0.6745
            else:
                return 0.6745


class ComplianceCheckTool(BaseTool):
    """Tool for regulatory and compliance checks"""
    name: str = "Compliance Check Tool"
    description: str = "Checks trading activities against regulatory requirements and limits"
    
    def _run(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Check if trade request complies with regulations"""
        try:
            checks = {}
            warnings = []
            violations = []
            
            # Check position limits
            current_position = trade_request.get("current_position", 0)
            requested_amount = trade_request.get("amount", 0)
            max_position = trade_request.get("max_position_limit", settings.max_position_size)
            
            if abs(current_position + requested_amount) > max_position:
                violations.append({
                    "type": "position_limit",
                    "message": f"Position exceeds maximum limit of {max_position}",
                    "current_position": current_position,
                    "requested_amount": requested_amount,
                    "resulting_position": current_position + requested_amount,
                    "limit": max_position
                })
            
            # Check risk limits
            portfolio_var = trade_request.get("portfolio_var", 0)
            trade_risk = trade_request.get("estimated_trade_risk", 0)
            max_risk = trade_request.get("max_risk_limit", settings.max_position_size * settings.risk_tolerance)
            
            if trade_risk > max_risk:
                violations.append({
                    "type": "risk_limit",
                    "message": f"Trade risk {trade_risk} exceeds maximum risk limit {max_risk}",
                    "trade_risk": trade_risk,
                    "max_risk": max_risk
                })
            
            # Check sector concentration
            sector_exposure = trade_request.get("sector_exposure", {})
            sector_limit = trade_request.get("sector_concentration_limit", 0.25)  # 25%
            
            for sector, exposure in sector_exposure.items():
                if exposure > sector_limit:
                    violations.append({
                        "type": "sector_concentration",
                        "message": f"Sector {sector} exposure {exposure:.2%} exceeds limit {sector_limit:.2%}",
                        "sector": sector,
                        "exposure": exposure,
                        "limit": sector_limit
                    })
            
            # Check concentration limits
            symbol_concentration = trade_request.get("symbol_concentration", {})
            symbol_limit = trade_request.get("symbol_concentration_limit", 0.10)  # 10%
            
            for symbol, exposure in symbol_concentration.items():
                if exposure > symbol_limit:
                    violations.append({
                        "type": "symbol_concentration",
                        "message": f"Symbol {symbol} concentration {exposure:.2%} exceeds limit {symbol_limit:.2%}",
                        "symbol": symbol,
                        "exposure": exposure,
                        "limit": symbol_limit
                    })
            
            # Check liquidity requirements
            avg_daily_volume = trade_request.get("avg_daily_volume", 0)
            requested_amount = trade_request.get("amount", 0)
            liquidity_ratio = trade_request.get("liquidity_ratio", 0.1)  # Max 10% of daily volume
            
            if avg_daily_volume > 0:
                volume_limit = avg_daily_volume * liquidity_ratio
                if requested_amount > volume_limit:
                    warnings.append({
                        "type": "liquidity_risk",
                        "message": f"Trade amount {requested_amount} exceeds 10% of daily volume {volume_limit:.0f}",
                        "requested_amount": requested_amount,
                        "daily_volume": avg_daily_volume,
                        "limit": volume_limit
                    })
            
            checks["violations"] = violations
            checks["warnings"] = warnings
            checks["passed"] = len(violations) == 0
            
            return {
                "compliance_check": checks,
                "trade_request": trade_request,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": f"Compliance check error: {e}"}


class ChiefRiskOfficer:
    """Chief Risk Officer Agent"""
    
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.logger = logging.getLogger(__name__)
        self.risk_cache = RiskCache(cache_manager)
        
        # Create tools
        self.tools = [
            RiskCalculationTool(),
            ComplianceCheckTool()
        ]
        
        # Create agent
        self.agent = Agent(
            role="Chief Risk Officer",
            goal="Ensure all trading activities comply with risk management policies and regulatory requirements",
            backstory="""You are an experienced Chief Risk Officer with deep expertise in quantitative risk management, 
                        portfolio analysis, and regulatory compliance. You are responsible for protecting the organization 
                        from financial losses while enabling profitable trading strategies.""",
            tools=self.tools,
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True,
            cache=True,
            llm_config={
                "model": "gpt-4",
                "temperature": 0.2,
                "max_tokens": 2000
            }
        )
    
    async def assess_portfolio_risk(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive portfolio risk assessment"""
        try:
            # Calculate various risk metrics
            risk_metrics = {}
            
            # Value at Risk
            var_result = self.tools[0]._run(portfolio_data, "var")
            if "error" not in var_result:
                risk_metrics["var"] = var_result
            
            # Volatility
            vol_result = self.tools[0]._run(portfolio_data, "volatility")
            if "error" not in vol_result:
                risk_metrics["volatility"] = vol_result
            
            # Correlation
            corr_result = self.tools[0]._run(portfolio_data, "correlation")
            if "error" not in corr_result:
                risk_metrics["correlation"] = corr_result
            
            # Drawdown
            dd_result = self.tools[0]._run(portfolio_data, "drawdown")
            if "error" not in dd_result:
                risk_metrics["drawdown"] = dd_result
            
            # Beta
            beta_result = self.tools[0]._run(portfolio_data, "beta")
            if "error" not in beta_result:
                risk_metrics["beta"] = beta_result
            
            # Calculate overall risk score
            risk_score = self._calculate_overall_risk_score(risk_metrics)
            
            assessment = {
                "portfolio_id": portfolio_data.get("portfolio_id", "default"),
                "risk_metrics": risk_metrics,
                "overall_risk_score": risk_score,
                "risk_level": self._categorize_risk_level(risk_score),
                "recommendations": self._generate_risk_recommendations(risk_metrics, risk_score),
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in memory and cache
            await memory_manager.store_risk_metrics(self.crew_id, assessment)
            await self.risk_cache.cache_risk_metrics(
                portfolio_data.get("portfolio_id", "default"), 
                assessment
            )
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Error in portfolio risk assessment: {e}")
            return {"error": str(e)}
    
    async def check_trade_compliance(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a trade request complies with all regulations"""
        try:
            compliance_result = self.tools[1]._run(trade_request)
            
            # Store compliance check in memory
            await memory_manager.store_agent_memory(
                self.crew_id, 
                "chief_risk_officer", 
                f"compliance_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                compliance_result
            )
            
            # Add approval requirement if violations exist
            if compliance_result.get("compliance_check", {}).get("violations"):
                await memory_manager.add_approval_request(
                    self.crew_id, 
                    {
                        "type": "compliance_violation",
                        "trade_request": trade_request,
                        "violations": compliance_result["compliance_check"]["violations"],
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            return compliance_result
            
        except Exception as e:
            self.logger.error(f"Error checking trade compliance: {e}")
            return {"error": str(e)}
    
    async def calculate_margin_requirements(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate margin requirements for positions"""
        try:
            total_margin = 0
            margin_breakdown = {}
            
            for symbol, position in positions.items():
                try:
                    # Get current price
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period="1d")
                    current_price = float(data['Close'].iloc[-1])
                    
                    # Calculate position value
                    position_value = abs(position.get("quantity", 0) * current_price)
                    
                    # Simplified margin calculation (in practice, use broker-specific rules)
                    if position.get("type") == "long":
                        margin_rate = 0.25  # 25% for long positions
                    else:  # short
                        margin_rate = 0.30  # 30% for short positions
                    
                    margin_required = position_value * margin_rate
                    total_margin += margin_required
                    
                    margin_breakdown[symbol] = {
                        "position_value": position_value,
                        "margin_rate": margin_rate,
                        "margin_required": margin_required
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Error calculating margin for {symbol}: {e}")
                    margin_breakdown[symbol] = {"error": str(e)}
            
            return {
                "total_margin_required": total_margin,
                "margin_breakdown": margin_breakdown,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating margin requirements: {e}")
            return {"error": str(e)}
    
    async def stress_test_portfolio(self, portfolio_data: Dict[str, Any], 
                                  stress_scenarios: List[str] = None) -> Dict[str, Any]:
        """Run stress tests on portfolio"""
        if not stress_scenarios:
            stress_scenarios = ["market_crash", "interest_rate_shock", "volatility_spike", "correlation_breakdown"]
        
        stress_results = {}
        
        for scenario in stress_scenarios:
            try:
                if scenario == "market_crash":
                    result = self._simulate_market_crash(portfolio_data)
                elif scenario == "interest_rate_shock":
                    result = self._simulate_interest_rate_shock(portfolio_data)
                elif scenario == "volatility_spike":
                    result = self._simulate_volatility_spike(portfolio_data)
                elif scenario == "correlation_breakdown":
                    result = self._simulate_correlation_breakdown(portfolio_data)
                else:
                    result = {"error": f"Unknown stress scenario: {scenario}"}
                
                stress_results[scenario] = result
                
            except Exception as e:
                self.logger.error(f"Error running stress test for {scenario}: {e}")
                stress_results[scenario] = {"error": str(e)}
        
        return {
            "stress_test_results": stress_results,
            "scenarios_tested": stress_scenarios,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_overall_risk_score(self, risk_metrics: Dict[str, Any]) -> float:
        """Calculate overall portfolio risk score (0-100)"""
        try:
            scores = []
            weights = []
            
            # VaR score (higher VaR = higher risk score)
            if "var" in risk_metrics and "portfolio_value" in risk_metrics["var"]:
                var_pct = risk_metrics["var"]["historical_var"] / risk_metrics["var"]["portfolio_value"]
                scores.append(min(var_pct * 1000, 100))  # Scale and cap at 100
                weights.append(0.3)
            
            # Volatility score
            if "volatility" in risk_metrics:
                vol_pct = risk_metrics["volatility"]["annualized_volatility"]
                scores.append(min(vol_pct * 100, 100))  # Scale annual vol to 0-100
                weights.append(0.25)
            
            # Drawdown score
            if "drawdown" in risk_metrics:
                dd_pct = abs(risk_metrics["drawdown"]["max_drawdown"]) * 100
                scores.append(min(dd_pct * 2, 100))  # Scale drawdown
                weights.append(0.25)
            
            # Beta score
            if "beta" in risk_metrics:
                beta = abs(risk_metrics["beta"]["beta"])
                beta_score = min(max(beta * 50, 0), 100)  # Scale beta
                scores.append(beta_score)
                weights.append(0.2)
            
            # Calculate weighted average
            if scores and weights:
                return sum(s * w for s, w in zip(scores, weights)) / sum(weights)
            else:
                return 50.0  # Default medium risk
                
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {e}")
            return 50.0
    
    def _categorize_risk_level(self, risk_score: float) -> str:
        """Categorize risk level based on score"""
        if risk_score < 20:
            return "Low"
        elif risk_score < 50:
            return "Medium"
        elif risk_score < 75:
            return "High"
        else:
            return "Very High"
    
    def _generate_risk_recommendations(self, risk_metrics: Dict[str, Any], risk_score: float) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        try:
            # VaR recommendations
            if "var" in risk_metrics:
                var_pct = risk_metrics["var"]["historical_var"] / risk_metrics["var"]["portfolio_value"]
                if var_pct > 0.05:  # 5%
                    recommendations.append("Consider reducing position sizes to lower VaR exposure")
            
            # Volatility recommendations
            if "volatility" in risk_metrics:
                ann_vol = risk_metrics["volatility"]["annualized_volatility"]
                if ann_vol > 0.3:  # 30% annual volatility
                    recommendations.append("Portfolio volatility is high; consider adding defensive assets")
            
            # Correlation recommendations
            if "correlation" in risk_metrics:
                avg_corr = risk_metrics["correlation"]["average_correlation"]
                if avg_corr > 0.7:
                    recommendations.append("High correlation detected; diversify across uncorrelated assets")
            
            # Drawdown recommendations
            if "drawdown" in risk_metrics:
                max_dd = abs(risk_metrics["drawdown"]["max_drawdown"])
                if max_dd > 0.2:  # 20%
                    recommendations.append("High maximum drawdown; implement stop-loss mechanisms")
            
            # Overall risk recommendations
            if risk_score > 75:
                recommendations.append("Overall risk level is very high; review and reduce exposure")
            elif risk_score < 20:
                recommendations.append("Risk level is very low; consider if returns are adequate")
            
            if not recommendations:
                recommendations.append("Portfolio risk metrics are within acceptable ranges")
                
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Unable to generate specific recommendations")
        
        return recommendations
    
    def _simulate_market_crash(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate market crash scenario"""
        try:
            positions = portfolio_data.get("positions", {})
            
            total_loss = 0
            position_losses = {}
            
            for symbol, position in positions.items():
                # Simulate 30% loss for equity positions
                position_value = abs(position.get("value", 0))
                loss = position_value * 0.30  # 30% loss
                total_loss += loss
                position_losses[symbol] = loss
            
            portfolio_value = sum(abs(pos.get("value", 0)) for pos in positions.values())
            loss_percentage = total_loss / portfolio_value if portfolio_value > 0 else 0
            
            return {
                "scenario": "market_crash",
                "shock_size": -0.30,
                "total_loss": total_loss,
                "loss_percentage": loss_percentage,
                "position_losses": position_losses,
                "recovery_time_estimate": "12-18 months"
            }
        except Exception as e:
            return {"error": f"Market crash simulation error: {e}"}
    
    def _simulate_interest_rate_shock(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate interest rate shock"""
        try:
            positions = portfolio_data.get("positions", {})
            
            total_impact = 0
            position_impacts = {}
            
            for symbol, position in positions.items():
                # Simulate 2% rate increase impact
                position_value = abs(position.get("value", 0))
                impact = position_value * 0.05  # 5% negative impact from rate increase
                total_impact += impact
                position_impacts[symbol] = impact
            
            portfolio_value = sum(abs(pos.get("value", 0)) for pos in positions.values())
            impact_percentage = total_impact / portfolio_value if portfolio_value > 0 else 0
            
            return {
                "scenario": "interest_rate_shock",
                "rate_increase": 0.02,
                "total_impact": total_impact,
                "impact_percentage": impact_percentage,
                "position_impacts": position_impacts
            }
        except Exception as e:
            return {"error": f"Interest rate shock simulation error: {e}"}
    
    def _simulate_volatility_spike(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate volatility spike"""
        try:
            positions = portfolio_data.get("positions", {})
            
            # Simulate increased volatility impact on options and leveraged positions
            total_impact = 0
            position_impacts = {}
            
            for symbol, position in positions.items():
                position_value = abs(position.get("value", 0))
                # Volatility spike affects options more than equities
                impact = position_value * 0.15  # 15% impact from volatility spike
                total_impact += impact
                position_impacts[symbol] = impact
            
            portfolio_value = sum(abs(pos.get("value", 0)) for pos in positions.values())
            impact_percentage = total_impact / portfolio_value if portfolio_value > 0 else 0
            
            return {
                "scenario": "volatility_spike",
                "volatility_multiplier": 3.0,
                "total_impact": total_impact,
                "impact_percentage": impact_percentage,
                "position_impacts": position_impacts
            }
        except Exception as e:
            return {"error": f"Volatility spike simulation error: {e}"}
    
    def _simulate_correlation_breakdown(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate correlation breakdown scenario"""
        try:
            # In correlation breakdown, diversification benefits disappear
            # Simulate increased portfolio volatility
            
            portfolio_value = portfolio_data.get("portfolio_value", 100000)
            # Simulate 25% increase in portfolio volatility
            additional_risk = portfolio_value * 0.25
            
            return {
                "scenario": "correlation_breakdown",
                "volatility_increase": 0.25,
                "additional_risk": additional_risk,
                "description": "Diversification benefits disappear, all assets move together"
            }
        except Exception as e:
            return {"error": f"Correlation breakdown simulation error: {e}"}
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance"""
        return self.agent


# Example usage function
async def create_chief_risk_officer(crew_id: str) -> ChiefRiskOfficer:
    """Factory function to create Chief Risk Officer"""
    cro = ChiefRiskOfficer(crew_id)
    
    # Initialize memory connections
    await memory_manager.connect()
    
    return cro