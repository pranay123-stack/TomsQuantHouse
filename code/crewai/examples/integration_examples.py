"""
Integration Examples for CrewAI Trading Agent System
Demonstrates how to integrate with the trading crew using various interfaces
"""
import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime

from orchestration.crew_orchestrator import create_crew_orchestrator
from orchestration.approval_workflow import ApprovalType, PriorityLevel
from api.server import app, TradeRequest, PortfolioRequest
import uvicorn


class TradingCrewExamples:
    """Examples demonstrating crew integration"""
    
    def __init__(self, crew_id: str = "example_crew"):
        self.crew_id = crew_id
        self.orchestrator = None
    
    async def setup(self):
        """Initialize the trading crew"""
        self.orchestrator = await create_crew_orchestrator(self.crew_id, async_mode=True)
        await self.orchestrator.initialize()
    
    async def example_1_complete_analysis(self):
        """Example 1: Run complete trading analysis"""
        print("=== Example 1: Complete Trading Analysis ===")
        
        symbol = "AAPL"
        
        try:
            # Run complete analysis
            result = await self.orchestrator.run_complete_analysis(symbol)
            
            print(f"Analysis Results for {symbol}:")
            print(json.dumps(result, indent=2, default=str))
            
            return result
            
        except Exception as e:
            print(f"Error in analysis: {e}")
            return None
    
    async def example_2_trade_execution(self):
        """Example 2: Execute a trade with approval workflow"""
        print("\n=== Example 2: Trade Execution with Approval ===")
        
        trade_request = {
            "symbol": "TSLA",
            "side": "buy",
            "quantity": 100,
            "order_type": "limit",
            "execution_strategy": "twap",
            "urgency": "normal",
            "max_price": 250.00
        }
        
        try:
            # Submit trade for execution
            result = await self.orchestrator.execute_trade_workflow(trade_request)
            
            print("Trade Execution Result:")
            print(json.dumps(result, indent=2, default=str))
            
            return result
            
        except Exception as e:
            print(f"Error in trade execution: {e}")
            return None
    
    async def example_3_portfolio_review(self):
        """Example 3: Comprehensive portfolio review"""
        print("\n=== Example 3: Portfolio Review ===")
        
        portfolio_data = {
            "positions": {
                "AAPL": {"quantity": 100, "avg_price": 150.0},
                "MSFT": {"quantity": 50, "avg_price": 300.0},
                "GOOGL": {"quantity": 20, "avg_price": 2500.0}
            },
            "cash": 10000.0,
            "total_value": 75000.0
        }
        
        try:
            # Run portfolio review
            result = await self.orchestrator.run_portfolio_review(portfolio_data)
            
            print("Portfolio Review Results:")
            print(json.dumps(result, indent=2, default=str))
            
            return result
            
        except Exception as e:
            print(f"Error in portfolio review: {e}")
            return None
    
    async def example_4_parallel_analysis(self):
        """Example 4: Analyze multiple symbols in parallel"""
        print("\n=== Example 4: Parallel Analysis ===")
        
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
        
        try:
            # Run parallel analysis
            result = await self.orchestrator.run_parallel_analysis(symbols)
            
            print("Parallel Analysis Results:")
            print(json.dumps(result, indent=2, default=str))
            
            return result
            
        except Exception as e:
            print(f"Error in parallel analysis: {e}")
            return None
    
    async def example_5_approval_workflow(self):
        """Example 5: Manual approval workflow management"""
        print("\n=== Example 5: Approval Workflow ===")
        
        try:
            # Submit a high-value trade that requires approval
            high_value_trade = {
                "symbol": "NVDA",
                "side": "buy",
                "quantity": 500,
                "order_type": "market",
                "trade_value": 50000.0  # High value requiring approval
            }
            
            # Submit for approval
            approval_id = await self.orchestrator.approval_workflow.submit_trade_approval(
                high_value_trade,
                requester="trading_system"
            )
            
            print(f"Submitted approval request: {approval_id}")
            
            # List pending approvals
            pending_approvals = await self.orchestrator.approval_workflow.list_pending_approvals()
            print("Pending approvals:", json.dumps(pending_approvals, indent=2, default=str))
            
            # Simulate approval decision
            if pending_approvals:
                approval_request = pending_approvals[0]
                approval_id = approval_request["request_id"]
                
                # Approve the trade
                success = await self.orchestrator.approval_workflow.process_approval(
                    approval_id,
                    approver="risk_manager",
                    decision="approved",
                    notes="Approved after risk assessment"
                )
                
                print(f"Approval processed: {success}")
            
            return {"approval_id": approval_id, "status": "processed"}
            
        except Exception as e:
            print(f"Error in approval workflow: {e}")
            return None
    
    async def example_6_monitoring_workflow(self):
        """Example 6: Set up continuous monitoring"""
        print("\n=== Example 6: Continuous Monitoring ===")
        
        symbols = ["^GSPC", "^DJI", "^IXIC", "AAPL", "MSFT"]
        
        try:
            # Run initial market monitoring
            result = await self.orchestrator.execution_trader.monitor_market_conditions(symbols)
            
            print("Market Monitoring Results:")
            print(json.dumps(result, indent=2, default=str))
            
            # Get crew metrics
            metrics = await self.orchestrator.get_crew_metrics()
            print("Crew Metrics:")
            print(json.dumps(metrics, indent=2, default=str))
            
            return result
            
        except Exception as e:
            print(f"Error in monitoring: {e}")
            return None
    
    async def example_7_ml_predictions(self):
        """Example 7: ML prediction workflow"""
        print("\n=== Example 7: ML Predictions ===")
        
        symbol = "AAPL"
        
        try:
            # Build prediction model
            print("Building ML model...")
            model_result = await self.orchestrator.ml_prediction_engineer.build_prediction_model(
                symbol, "random_forest"
            )
            print("Model built:", model_result.get("model_type", "Unknown"))
            
            # Generate predictions
            print("Generating predictions...")
            prediction_result = await self.orchestrator.ml_prediction_engineer.make_prediction(
                symbol, "random_forest"
            )
            print("Prediction result:", prediction_result)
            
            # Run backtest
            print("Running backtest...")
            backtest_result = await self.orchestrator.ml_prediction_engineer.backtest_strategy(
                symbol, "random_forest"
            )
            print("Backtest result:", backtest_result.get("performance", {}))
            
            return {
                "model": model_result,
                "prediction": prediction_result,
                "backtest": backtest_result
            }
            
        except Exception as e:
            print(f"Error in ML predictions: {e}")
            return None
    
    async def example_8_risk_analysis(self):
        """Example 8: Risk analysis workflow"""
        print("\n=== Example 8: Risk Analysis ===")
        
        try:
            # Assess portfolio risk
            portfolio_data = {
                "portfolio_id": "example_portfolio",
                "positions": {
                    "AAPL": {"value": 50000, "quantity": 100},
                    "MSFT": {"value": 30000, "quantity": 50}
                },
                "returns_data": [0.01, -0.02, 0.03, -0.01, 0.02] * 50  # Simulated returns
            }
            
            # Run risk assessment
            risk_result = await self.orchestrator.chief_risk_officer.assess_portfolio_risk(portfolio_data)
            print("Risk Assessment Results:")
            print(json.dumps(risk_result, indent=2, default=str))
            
            # Run stress tests
            stress_result = await self.orchestrator.chief_risk_officer.stress_test_portfolio(portfolio_data)
            print("Stress Test Results:")
            print(json.dumps(stress_result, indent=2, default=str))
            
            return {
                "risk_assessment": risk_result,
                "stress_tests": stress_result
            }
            
        except Exception as e:
            print(f"Error in risk analysis: {e}")
            return None
    
    async def run_all_examples(self):
        """Run all examples in sequence"""
        print("Starting CrewAI Trading System Examples")
        print("=" * 50)
        
        # Setup
        await self.setup()
        
        # Run examples
        results = {}
        
        try:
            results["complete_analysis"] = await self.example_1_complete_analysis()
            results["trade_execution"] = await self.example_2_trade_execution()
            results["portfolio_review"] = await self.example_3_portfolio_review()
            results["parallel_analysis"] = await self.example_4_parallel_analysis()
            results["approval_workflow"] = await self.example_5_approval_workflow()
            results["monitoring"] = await self.example_6_monitoring_workflow()
            results["ml_predictions"] = await self.example_7_ml_predictions()
            results["risk_analysis"] = await self.example_8_risk_analysis()
            
            print("\n" + "=" * 50)
            print("All examples completed successfully!")
            
        except Exception as e:
            print(f"Error running examples: {e}")
        
        finally:
            # Cleanup
            await self.cleanup()
        
        return results
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.orchestrator:
            await self.orchestrator.shutdown()


class APIIntegrationExamples:
    """Examples using the FastAPI interface"""
    
    @staticmethod
    def create_example_requests():
        """Create example API requests"""
        
        # Trade request example
        trade_request = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "order_type": "limit",
            "execution_strategy": "twap",
            "urgency": "normal",
            "max_price": 150.00
        }
        
        # Portfolio request example
        portfolio_request = {
            "positions": {
                "AAPL": {"quantity": 100, "avg_price": 150.0},
                "MSFT": {"quantity": 50, "avg_price": 300.0}
            },
            "cash": 25000.0,
            "total_value": 75000.0
        }
        
        # Analysis request example
        analysis_request = {
            "symbols": ["AAPL", "MSFT", "GOOGL"],
            "analysis_type": "complete",
            "include_predictions": True,
            "include_risk_analysis": True
        }
        
        return {
            "trade_request": trade_request,
            "portfolio_request": portfolio_request,
            "analysis_request": analysis_request
        }
    
    @staticmethod
    def example_curl_requests():
        """Example curl commands for API testing"""
        
        commands = [
            # Health check
            "curl -X GET http://localhost:8000/health",
            
            # Initialize crew
            "curl -X POST http://localhost:8000/crew/initialize",
            
            # Run analysis
            """curl -X POST http://localhost:8000/analysis/complete \\
                -H "Content-Type: application/json" \\
                -d '{"symbols": ["AAPL"], "analysis_type": "complete"}'""",
            
            # Submit trade
            """curl -X POST http://localhost:8000/trade/submit \\
                -H "Content-Type: application/json" \\
                -d '{"symbol": "AAPL", "side": "buy", "quantity": 100}'""",
            
            # Portfolio review
            """curl -X POST http://localhost:8000/portfolio/review \\
                -H "Content-Type: application/json" \\
                -d '{"positions": {"AAPL": {"quantity": 100}}, "cash": 10000, "total_value": 25000}'""",
            
            # List pending approvals
            "curl -X GET http://localhost:8000/approvals/pending",
            
            # Get crew metrics
            "curl -X GET http://localhost:8000/metrics/crew"
        ]
        
        return commands


class CustomIntegrationExample:
    """Example of custom integration"""
    
    def __init__(self, crew_id: str = "custom_crew"):
        self.crew_id = crew_id
        self.orchestrator = None
    
    async def custom_trading_strategy(self):
        """Example of implementing a custom trading strategy"""
        print("Implementing custom trading strategy...")
        
        try:
            # Setup
            self.orchestrator = await create_crew_orchestrator(self.crew_id, async_mode=True)
            await self.orchestrator.initialize()
            
            # Step 1: Analyze market conditions
            market_analysis = await self.orchestrator.market_research_analyst.analyze_market_conditions()
            
            # Step 2: Identify opportunities
            opportunities = await self.orchestrator.market_research_analyst.identify_opportunities()
            
            # Step 3: For each opportunity, run full analysis
            for opportunity in opportunities.get("opportunities", []):
                symbol = opportunity.get("symbol")
                if symbol:
                    print(f"Analyzing opportunity: {symbol}")
                    
                    # Complete analysis
                    analysis = await self.orchestrator.run_complete_analysis(symbol)
                    
                    # Risk assessment
                    portfolio_data = {"portfolio_value": 50000}
                    risk_assessment = await self.orchestrator.chief_risk_officer.assess_portfolio_risk(portfolio_data)
                    
                    # Decision logic
                    if self._should_execute_trade(analysis, risk_assessment):
                        print(f"Executing trade for {symbol}")
                        await self._execute_trade(symbol, analysis)
            
        except Exception as e:
            print(f"Error in custom strategy: {e}")
        
        finally:
            if self.orchestrator:
                await self.orchestrator.shutdown()
    
    def _should_execute_trade(self, analysis: Dict[str, Any], risk_assessment: Dict[str, Any]) -> bool:
        """Custom logic to decide if trade should be executed"""
        try:
            # Example decision criteria
            summary = analysis.get("summary", {})
            recommendation = summary.get("recommendation", "hold")
            
            risk_score = risk_assessment.get("overall_risk_score", 50)
            
            # Execute only strong buy signals with acceptable risk
            if recommendation == "buy" and risk_score < 70:
                return True
            
            return False
            
        except Exception as e:
            print(f"Error in decision logic: {e}")
            return False
    
    async def _execute_trade(self, symbol: str, analysis: Dict[str, Any]):
        """Execute trade based on analysis"""
        try:
            trade_request = {
                "symbol": symbol,
                "side": "buy",
                "quantity": 100,
                "execution_strategy": "twap"
            }
            
            result = await self.orchestrator.execute_trade_workflow(trade_request)
            print(f"Trade execution result: {result}")
            
        except Exception as e:
            print(f"Error executing trade: {e}")


# Main execution functions
async def run_basic_examples():
    """Run basic integration examples"""
    examples = TradingCrewExamples()
    return await examples.run_all_examples()


async def run_custom_example():
    """Run custom integration example"""
    custom = CustomIntegrationExample()
    await custom.custom_trading_strategy()


async def start_api_server():
    """Start the FastAPI server"""
    print("Starting FastAPI server on http://localhost:8000")
    print("API documentation available at http://localhost:8000/docs")
    
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "examples":
            asyncio.run(run_basic_examples())
        elif command == "custom":
            asyncio.run(run_custom_example())
        elif command == "api":
            start_api_server()
        else:
            print("Usage: python examples.py [examples|custom|api]")
    else:
        print("CrewAI Trading System Integration Examples")
        print("Usage: python examples.py [examples|custom|api]")
        print()
        print("Commands:")
        print("  examples - Run basic integration examples")
        print("  custom   - Run custom strategy example")
        print("  api      - Start FastAPI server")