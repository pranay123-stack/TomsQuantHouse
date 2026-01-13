"""
Crew Orchestration System
Coordinates all agents, tasks, and workflows for the trading crew
"""
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from crewai import Crew, Agent, Task
from crewai.memory import LongTermMemory
from utils.memory_manager import memory_manager
from cache.cache_manager import CacheManager
from orchestration.approval_workflow import ApprovalWorkflow, TradeApprovalWorkflow, ApprovalType, PriorityLevel
from tasks.task_definitions import TaskOrchestrator, create_trading_analysis_workflow, create_trade_execution_workflow, create_portfolio_review_workflow
from agents.market_research_analyst import create_market_research_analyst
from agents.ml_prediction_engineer import create_ml_prediction_engineer
from agents.chief_risk_officer import create_chief_risk_officer
from agents.execution_trader import create_execution_trader
from config.settings import settings
import logging
import asyncio


class CrewOrchestrator:
    """Main orchestrator for the trading agent crew"""
    
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.task_orchestrator = TaskOrchestrator(crew_id)
        self.approval_workflow = None
        self.crew = None
        self.cache_manager = None
        
        # Agent instances
        self.market_research_analyst = None
        self.ml_prediction_engineer = None
        self.chief_risk_officer = None
        self.execution_trader = None
        
        # Workflow status
        self.active_workflows = {}
        self.completed_tasks = {}
        self.cached_results = {}
        
        # Performance metrics
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "approval_requests": 0,
            "auto_approvals": 0,
            "execution_success_rate": 0.0
        }
    
    async def initialize(self):
        """Initialize all components"""
        try:
            # Initialize memory
            await memory_manager.connect()
            
            # Initialize cache manager
            redis_client = memory_manager.get_redis_client()
            self.cache_manager = CacheManager(redis_client)
            
            # Set global cache manager reference
            from cache.cache_manager import set_cache_manager
            set_cache_manager(redis_client)
            
            # Create agents
            self.market_research_analyst = await create_market_research_analyst(self.crew_id)
            self.ml_prediction_engineer = await create_ml_prediction_engineer(self.crew_id)
            self.chief_risk_officer = await create_chief_risk_officer(self.crew_id)
            self.execution_trader = await create_execution_trader(self.crew_id)
            
            # Initialize approval workflow
            self.approval_workflow = TradeApprovalWorkflow(self.crew_id)
            
            # Create crew
            self.crew = Crew(
                agents=[
                    self.market_research_analyst.get_agent(),
                    self.ml_prediction_engineer.get_agent(),
                    self.chief_risk_officer.get_agent(),
                    self.execution_trader.get_agent()
                ],
                verbose=True
            )
            
            self.logger.info(f"Crew {self.crew_id} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing crew: {e}")
            raise
    
    async def run_complete_analysis(self, symbol: str) -> Dict[str, Any]:
        """Run complete trading analysis workflow"""
        try:
            workflow_id = f"analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create workflow tasks
            tasks = create_trading_analysis_workflow(symbol)
            
            # Execute tasks with dependencies
            results = {}
            
            # Step 1: Market Research
            market_task = tasks["market_research"]
            market_result = await self._execute_task(market_task, "market_research")
            results["market_research"] = market_result
            
            if "error" not in market_result:
                # Step 2: ML Prediction (depends on market research)
                ml_task = tasks["ml_prediction"]
                ml_result = await self._execute_task(ml_task, "ml_prediction", 
                                                   context=market_result)
                results["ml_prediction"] = ml_result
                
                # Step 3: Risk Assessment (depends on ML prediction)
                risk_task = tasks["risk_assessment"]
                risk_result = await self._execute_task(risk_task, "risk_assessment",
                                                     context=ml_result)
                results["risk_assessment"] = risk_result
                
                # Step 4: Execution Analysis (depends on all previous)
                execution_task = tasks["execution_analysis"]
                execution_result = await self._execute_task(execution_task, "execution_analysis",
                                                          context=results)
                results["execution_analysis"] = execution_result
            
            # Store complete workflow results
            await memory_manager.store_crew_memory(
                self.crew_id, 
                f"complete_analysis_{symbol}",
                {
                    "workflow_id": workflow_id,
                    "symbol": symbol,
                    "results": results,
                    "timestamp": datetime.now().isoformat(),
                    "summary": self._generate_analysis_summary(results)
                }
            )
            
            self.metrics["tasks_completed"] += len(results)
            return results
            
        except Exception as e:
            self.logger.error(f"Error in complete analysis: {e}")
            self.metrics["tasks_failed"] += 1
            return {"error": str(e)}
    
    async def execute_trade_workflow(self, trade_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete trade workflow with approvals"""
        try:
            workflow_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Step 1: Submit for approval
            approval_id = await self.approval_workflow.submit_trade_approval(
                trade_request, 
                requester="orchestrator"
            )
            
            self.metrics["approval_requests"] += 1
            
            # Check if auto-approved
            approval_status = await self.approval_workflow.get_approval_status(approval_id)
            
            if approval_status and approval_status.get("status") == "approved":
                self.metrics["auto_approvals"] += 1
                
                # Execute approved trade
                execution_result = await self.execution_trader.execute_trade(trade_request)
                
                if "error" not in execution_result:
                    # Update metrics
                    self.metrics["execution_success_rate"] = (
                        (self.metrics["execution_success_rate"] * self.metrics["tasks_completed"] + 1) / 
                        (self.metrics["tasks_completed"] + 1)
                    )
                
                # Store workflow results
                await memory_manager.store_crew_memory(
                    self.crew_id,
                    f"trade_workflow_{workflow_id}",
                    {
                        "workflow_id": workflow_id,
                        "trade_request": trade_request,
                        "approval_id": approval_id,
                        "execution_result": execution_result,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return {
                    "workflow_id": workflow_id,
                    "approval_status": "approved",
                    "execution_result": execution_result
                }
            else:
                # Await manual approval
                return {
                    "workflow_id": workflow_id,
                    "approval_id": approval_id,
                    "status": "pending_approval",
                    "message": "Trade submitted for approval"
                }
            
        except Exception as e:
            self.logger.error(f"Error in trade workflow: {e}")
            return {"error": str(e)}
    
    async def run_portfolio_review(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive portfolio review"""
        try:
            workflow_id = f"portfolio_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create workflow tasks
            tasks = create_portfolio_review_workflow(portfolio_data)
            
            # Execute tasks in parallel where possible
            results = {}
            
            # Step 1: Market Analysis and Risk Assessment (can run in parallel)
            market_task = tasks["market_analysis"]
            risk_task = tasks["risk_assessment"]
            
            market_result, risk_result = await asyncio.gather(
                self._execute_task(market_task, "market_analysis"),
                self._execute_task(risk_task, "risk_assessment")
            )
            
            results["market_analysis"] = market_result
            results["risk_assessment"] = risk_result
            
            # Step 2: Execution Performance Analysis
            perf_task = tasks["performance_analysis"]
            perf_result = await self._execute_task(perf_task, "performance_analysis")
            results["performance_analysis"] = perf_result
            
            # Step 3: Stress Testing
            stress_task = tasks["stress_testing"]
            stress_result = await self._execute_task(stress_task, "stress_testing", 
                                                   context=risk_result)
            results["stress_testing"] = stress_result
            
            # Generate portfolio recommendations
            recommendations = self._generate_portfolio_recommendations(results)
            
            # Store results
            review_results = {
                "workflow_id": workflow_id,
                "portfolio_data": portfolio_data,
                "results": results,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
            await memory_manager.store_crew_memory(
                self.crew_id,
                f"portfolio_review_{workflow_id}",
                review_results
            )
            
            return review_results
            
        except Exception as e:
            self.logger.error(f"Error in portfolio review: {e}")
            return {"error": str(e)}
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a specific workflow"""
        try:
            # Get from memory
            memory_data = await memory_manager.get_crew_memory(self.crew_id, workflow_id)
            
            if memory_data:
                return {
                    "workflow_id": workflow_id,
                    "status": "completed",
                    "data": memory_data
                }
            
            # Check active workflows
            if workflow_id in self.active_workflows:
                return {
                    "workflow_id": workflow_id,
                    "status": "running",
                    "progress": self.active_workflows[workflow_id]
                }
            
            return {
                "workflow_id": workflow_id,
                "status": "not_found"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting workflow status: {e}")
            return {"error": str(e)}
    
    async def list_workflows(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all workflows"""
        try:
            # Get all crew memory
            memory_data = await memory_manager.get_crew_memory(self.crew_id)
            
            workflows = []
            for key, value in memory_data.items():
                if isinstance(value, dict) and "workflow_id" in value:
                    workflow_info = {
                        "workflow_id": value.get("workflow_id"),
                        "type": value.get("type", "unknown"),
                        "status": value.get("status", "completed"),
                        "timestamp": value.get("timestamp"),
                        "symbol": value.get("symbol")
                    }
                    
                    if status_filter is None or workflow_info["status"] == status_filter:
                        workflows.append(workflow_info)
            
            return sorted(workflows, key=lambda x: x.get("timestamp", ""), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error listing workflows: {e}")
            return []
    
    async def get_crew_metrics(self) -> Dict[str, Any]:
        """Get crew performance metrics"""
        return {
            **self.metrics,
            "active_workflows": len(self.active_workflows),
            "cached_results": len(self.cached_results),
            "memory_usage": await self._get_memory_usage(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def shutdown(self):
        """Shutdown crew and cleanup resources"""
        try:
            # Close memory connections
            await memory_manager.disconnect()
            
            self.logger.info(f"Crew {self.crew_id} shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def _execute_task(self, task: Task, task_type: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a single task with context"""
        try:
            # Check cache first
            cache_key = f"{task_type}_{hash(str(task.description))}"
            cached_result = await memory_manager.get_crew_memory(self.crew_id, f"task_cache_{cache_key}")
            
            if cached_result:
                return cached_result
            
            # Add context to task if provided
            if context:
                enhanced_description = f"{task.description}\n\nContext: {str(context)}"
                task.description = enhanced_description
            
            # Execute task using crew
            result = self.crew.kickoff(task)
            
            # Parse result
            if hasattr(result, 'raw'):
                try:
                    parsed_result = eval(result.raw)  # In practice, use proper JSON parsing
                except:
                    parsed_result = {"output": result.raw}
            else:
                parsed_result = {"output": str(result)}
            
            # Cache result
            await memory_manager.store_crew_memory(
                self.crew_id,
                f"task_cache_{cache_key}",
                parsed_result,
                ttl=1800  # 30 minutes
            )
            
            return parsed_result
            
        except Exception as e:
            self.logger.error(f"Error executing task {task_type}: {e}")
            return {"error": str(e)}
    
    def _generate_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of analysis results"""
        try:
            summary = {
                "market_sentiment": "neutral",
                "prediction_confidence": 0.0,
                "risk_level": "medium",
                "recommendation": "hold",
                "key_insights": []
            }
            
            # Extract insights from results
            if "market_research" in results and "error" not in results["market_research"]:
                summary["market_sentiment"] = results["market_research"].get("sentiment", "neutral")
                summary["key_insights"].append("Market research completed")
            
            if "ml_prediction" in results and "error" not in results["ml_prediction"]:
                prediction_conf = results["ml_prediction"].get("confidence", 0.5)
                summary["prediction_confidence"] = prediction_conf
                summary["key_insights"].append("ML prediction generated")
            
            if "risk_assessment" in results and "error" not in results["risk_assessment"]:
                risk_level = results["risk_assessment"].get("overall_risk_score", 50)
                summary["risk_level"] = "high" if risk_level > 75 else "medium" if risk_level > 25 else "low"
                summary["key_insights"].append("Risk assessment completed")
            
            # Generate overall recommendation
            if summary["prediction_confidence"] > 0.7 and summary["risk_level"] in ["low", "medium"]:
                summary["recommendation"] = "buy"
            elif summary["prediction_confidence"] < 0.3 or summary["risk_level"] == "high":
                summary["recommendation"] = "sell"
            else:
                summary["recommendation"] = "hold"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating analysis summary: {e}")
            return {"recommendation": "hold", "error": str(e)}
    
    def _generate_portfolio_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate portfolio recommendations"""
        recommendations = []
        
        try:
            # Risk-based recommendations
            if "risk_assessment" in results and "error" not in results["risk_assessment"]:
                risk_data = results["risk_assessment"]
                risk_score = risk_data.get("overall_risk_score", 50)
                
                if risk_score > 80:
                    recommendations.append("Portfolio risk is very high - consider reducing position sizes")
                elif risk_score < 20:
                    recommendations.append("Portfolio risk is very low - consider if returns are adequate")
            
            # Market-based recommendations
            if "market_analysis" in results and "error" not in results["market_analysis"]:
                market_data = results["market_analysis"]
                market_sentiment = market_data.get("sentiment", "neutral")
                
                if market_sentiment == "positive":
                    recommendations.append("Market sentiment is positive - consider increasing exposure")
                elif market_sentiment == "negative":
                    recommendations.append("Market sentiment is negative - consider defensive positioning")
            
            # Performance-based recommendations
            if "performance_analysis" in results and "error" not in results["performance_analysis"]:
                perf_data = results["performance_analysis"]
                total_return = perf_data.get("total_return", 0)
                
                if total_return < -0.05:
                    recommendations.append("Portfolio underperforming - review strategy and positions")
                elif total_return > 0.15:
                    recommendations.append("Strong performance - consider taking profits on winners")
            
            # Stress test recommendations
            if "stress_testing" in results and "error" not in results["stress_testing"]:
                stress_data = results["stress_testing"]
                
                for scenario, result in stress_data.get("stress_test_results", {}).items():
                    if isinstance(result, dict):
                        loss_pct = result.get("loss_percentage", 0)
                        if loss_pct > 0.2:  # 20% loss
                            recommendations.append(f"High vulnerability to {scenario} - consider hedging")
            
            if not recommendations:
                recommendations.append("Portfolio metrics are within acceptable ranges")
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Unable to generate specific recommendations")
        
        return recommendations
    
    async def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            cache_stats = await self.cache_manager.get_cache_stats()
            memory_data = await memory_manager.get_crew_memory(self.crew_id)
            
            return {
                "cache_entries": cache_stats.get("total_entries", 0),
                "memory_entries": len(memory_data) if memory_data else 0,
                "categories": cache_stats.get("categories", {})
            }
            
        except Exception as e:
            self.logger.error(f"Error getting memory usage: {e}")
            return {}


class AsyncCrewOrchestrator(CrewOrchestrator):
    """Async version of CrewOrchestrator with enhanced async support"""
    
    async def run_parallel_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """Run analysis for multiple symbols in parallel"""
        try:
            tasks = []
            for symbol in symbols:
                task = self.run_complete_analysis(symbol)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            analysis_results = {}
            for i, result in enumerate(results):
                symbol = symbols[i]
                if isinstance(result, Exception):
                    analysis_results[symbol] = {"error": str(result)}
                else:
                    analysis_results[symbol] = result
            
            # Store combined results
            await memory_manager.store_crew_memory(
                self.crew_id,
                f"parallel_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                {
                    "symbols": symbols,
                    "results": analysis_results,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error in parallel analysis: {e}")
            return {"error": str(e)}
    
    async def run_continous_monitoring(self, symbols: List[str], interval_minutes: int = 60):
        """Run continuous market monitoring"""
        self.logger.info(f"Starting continuous monitoring for {symbols}")
        
        while True:
            try:
                # Run analysis for all symbols
                results = await self.run_parallel_analysis(symbols)
                
                # Check for alerts
                await self._check_for_alerts(results)
                
                # Wait for next cycle
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _check_for_alerts(self, results: Dict[str, Any]):
        """Check results for alerts that require attention"""
        try:
            alerts = []
            
            for symbol, result in results.items():
                if "error" in result:
                    alerts.append({
                        "type": "analysis_error",
                        "symbol": symbol,
                        "message": f"Analysis failed for {symbol}: {result['error']}"
                    })
                    continue
                
                # Check for high-risk situations
                if "risk_assessment" in result:
                    risk_score = result["risk_assessment"].get("overall_risk_score", 0)
                    if risk_score > 85:
                        alerts.append({
                            "type": "high_risk",
                            "symbol": symbol,
                            "risk_score": risk_score,
                            "message": f"High risk detected for {symbol}: {risk_score}"
                        })
                
                # Check for strong signals
                if "ml_prediction" in result:
                    confidence = result["ml_prediction"].get("confidence", 0)
                    if confidence > 0.85 or confidence < 0.15:
                        alerts.append({
                            "type": "strong_signal",
                            "symbol": symbol,
                            "confidence": confidence,
                            "message": f"Strong signal for {symbol}: confidence {confidence}"
                        })
            
            # Store alerts in memory
            if alerts:
                await memory_manager.store_crew_memory(
                    self.crew_id,
                    f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    {
                        "alerts": alerts,
                        "timestamp": datetime.now().isoformat()
                    },
                    ttl=3600  # 1 hour
                )
            
        except Exception as e:
            self.logger.error(f"Error checking for alerts: {e}")


class AsyncCrewOrchestrator(CrewOrchestrator):
    """Async version of CrewOrchestrator with enhanced async support"""
    
    async def run_parallel_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """Run analysis for multiple symbols in parallel"""
        try:
            tasks = []
            for symbol in symbols:
                task = self.run_complete_analysis(symbol)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            analysis_results = {}
            for i, result in enumerate(results):
                symbol = symbols[i]
                if isinstance(result, Exception):
                    analysis_results[symbol] = {"error": str(result)}
                else:
                    analysis_results[symbol] = result
            
            # Store combined results
            await memory_manager.store_crew_memory(
                self.crew_id,
                f"parallel_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                {
                    "symbols": symbols,
                    "results": analysis_results,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error in parallel analysis: {e}")
            return {"error": str(e)}
    
    async def run_continous_monitoring(self, symbols: List[str], interval_minutes: int = 60):
        """Run continuous market monitoring"""
        self.logger.info(f"Starting continuous monitoring for {symbols}")
        
        while True:
            try:
                # Run analysis for all symbols
                results = await self.run_parallel_analysis(symbols)
                
                # Check for alerts
                await self._check_for_alerts(results)
                
                # Wait for next cycle
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _check_for_alerts(self, results: Dict[str, Any]):
        """Check results for alerts that require attention"""
        try:
            alerts = []
            
            for symbol, result in results.items():
                if "error" in result:
                    alerts.append({
                        "type": "analysis_error",
                        "symbol": symbol,
                        "message": f"Analysis failed for {symbol}: {result['error']}"
                    })
                    continue
                
                # Check for high-risk situations
                if "risk_assessment" in result:
                    risk_score = result["risk_assessment"].get("overall_risk_score", 0)
                    if risk_score > 85:
                        alerts.append({
                            "type": "high_risk",
                            "symbol": symbol,
                            "risk_score": risk_score,
                            "message": f"High risk detected for {symbol}: {risk_score}"
                        })
                
                # Check for strong signals
                if "ml_prediction" in result:
                    confidence = result["ml_prediction"].get("confidence", 0)
                    if confidence > 0.85 or confidence < 0.15:
                        alerts.append({
                            "type": "strong_signal",
                            "symbol": symbol,
                            "confidence": confidence,
                            "message": f"Strong signal for {symbol}: confidence {confidence}"
                        })
            
            # Store alerts in memory
            if alerts:
                await memory_manager.store_crew_memory(
                    self.crew_id,
                    f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    {
                        "alerts": alerts,
                        "timestamp": datetime.now().isoformat()
                    },
                    ttl=3600  # 1 hour
                )
            
        except Exception as e:
            self.logger.error(f"Error checking for alerts: {e}")


# Factory function
async def create_crew_orchestrator(crew_id: str, async_mode: bool = False) -> CrewOrchestrator:
    """Factory function to create crew orchestrator"""
    if async_mode:
        return AsyncCrewOrchestrator(crew_id)
    else:
        return CrewOrchestrator(crew_id)