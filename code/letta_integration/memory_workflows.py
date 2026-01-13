#!/usr/bin/env python3
"""
Memory Update Workflows for Agent Learning Persistence
Handles structured workflows for updating agent memory across trading sessions
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import queue
import threading
from abc import ABC, abstractmethod

from advanced_memory_manager import (
    AdvancedMemoryManager, 
    MemoryBlockType, 
    MemoryPriority, 
    MemoryRetentionPolicy,
    TradingPattern,
    MarketLearning,
    PerformanceInsight
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowType(Enum):
    """Types of memory update workflows"""
    TRADE_ANALYSIS = "trade_analysis"
    STRATEGY_EVOLUTION = "strategy_evolution"
    RISK_ASSESSMENT = "risk_assessment"
    MARKET_LEARNING = "market_learning"
    PERFORMANCE_REVIEW = "performance_review"
    PATTERN_DISCOVERY = "pattern_discovery"
    REGIME_CHANGE = "regime_change"
    CORRELATION_UPDATE = "correlation_update"


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Individual step in a workflow"""
    step_id: str
    name: str
    description: str
    execute_func: Callable
    dependencies: List[str]
    timeout: int = 300  # 5 minutes default
    retry_count: int = 0
    max_retries: int = 3
    error_handling: str = "stop"  # stop, continue, retry


@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    workflow_id: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime]
    steps_completed: List[str]
    steps_failed: List[str]
    outputs: Dict[str, Any]
    errors: List[str]
    metrics: Dict[str, Any]


@dataclass
class TradeEvent:
    """Structured trade event for analysis"""
    trade_id: str
    symbol: str
    action: str  # buy, sell
    quantity: float
    entry_price: float
    exit_price: Optional[float]
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: Optional[float]
    strategy: str
    signal_source: str
    confidence: float
    risk_metrics: Dict[str, float]
    market_conditions: Dict[str, Any]
    outcome: Optional[str]  # win, loss, partial, pending


@dataclass
class MarketEvent:
    """Market event for learning"""
    event_id: str
    event_type: str  # volatility_spike, trend_change, news, etc.
    timestamp: datetime
    symbol: str
    severity: str
    impact_metrics: Dict[str, float]
    market_conditions: Dict[str, Any]
    strategy_impact: Dict[str, Any]
    learning_points: List[str]


class WorkflowExecutor:
    """Executes memory update workflows"""
    
    def __init__(self, memory_manager: AdvancedMemoryManager):
        self.memory_manager = memory_manager
        self.active_workflows = {}
        self.workflow_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.step_registry = self._register_step_types()
    
    def _register_step_types(self) -> Dict[str, Callable]:
        """Register available workflow step types"""
        return {
            "analyze_trade_outcome": self._analyze_trade_outcome,
            "update_strategy_performance": self._update_strategy_performance,
            "discover_patterns": self._discover_patterns,
            "assess_risk_events": self._assess_risk_events,
            "update_market_learning": self._update_market_learning,
            "analyze_performance": self._analyze_performance,
            "validate_predictions": self._validate_predictions,
            "generate_insights": self._generate_insights,
            "update_correlations": self._update_correlations,
            "archive_old_data": self._archive_old_data
        }
    
    async def execute_workflow(self, 
                             workflow_type: WorkflowType,
                             agent_id: str,
                             data: Dict[str, Any],
                             priority: str = "normal") -> str:
        """Execute a memory update workflow"""
        
        workflow_id = f"{workflow_type.value}_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Create workflow steps based on type
            steps = self._create_workflow_steps(workflow_type, data)
            
            # Create workflow result tracker
            workflow_result = WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.RUNNING,
                start_time=datetime.now(),
                end_time=None,
                steps_completed=[],
                steps_failed=[],
                outputs={},
                errors=[],
                metrics={}
            )
            
            # Store active workflow
            self.active_workflows[workflow_id] = workflow_result
            
            # Execute workflow steps
            if priority == "high":
                result = await self._execute_workflow_sync(workflow_id, steps, data)
            else:
                result = await self._execute_workflow_async(workflow_id, steps, data)
            
            return workflow_id
            
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {e}")
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id].status = WorkflowStatus.FAILED
                self.active_workflows[workflow_id].errors.append(str(e))
            return workflow_id
    
    def _create_workflow_steps(self, workflow_type: WorkflowType, data: Dict[str, Any]) -> List[WorkflowStep]:
        """Create workflow steps based on type"""
        
        steps = []
        
        if workflow_type == WorkflowType.TRADE_ANALYSIS:
            steps = [
                WorkflowStep(
                    step_id="validate_trade_data",
                    name="Validate Trade Data",
                    description="Validate and clean trade event data",
                    execute_func=self.step_registry["validate_trade_data"],
                    dependencies=[],
                    timeout=60
                ),
                WorkflowStep(
                    step_id="analyze_trade_outcome",
                    name="Analyze Trade Outcome",
                    description="Analyze trade outcome and update memory",
                    execute_func=self.step_registry["analyze_trade_outcome"],
                    dependencies=["validate_trade_data"],
                    timeout=300
                ),
                WorkflowStep(
                    step_id="update_strategy_performance",
                    name="Update Strategy Performance",
                    description="Update strategy performance metrics",
                    execute_func=self.step_registry["update_strategy_performance"],
                    dependencies=["analyze_trade_outcome"],
                    timeout=180
                )
            ]
        
        elif workflow_type == WorkflowType.STRATEGY_EVOLUTION:
            steps = [
                WorkflowStep(
                    step_id="analyze_performance",
                    name="Analyze Performance",
                    description="Analyze current strategy performance",
                    execute_func=self.step_registry["analyze_performance"],
                    dependencies=[],
                    timeout=300
                ),
                WorkflowStep(
                    step_id="discover_patterns",
                    name="Discover Patterns",
                    description="Discover new trading patterns",
                    execute_func=self.step_registry["discover_patterns"],
                    dependencies=["analyze_performance"],
                    timeout=600
                ),
                WorkflowStep(
                    step_id="generate_insights",
                    name="Generate Insights",
                    description="Generate actionable insights",
                    execute_func=self.step_registry["generate_insights"],
                    dependencies=["discover_patterns"],
                    timeout=180
                )
            ]
        
        elif workflow_type == WorkflowType.MARKET_LEARNING:
            steps = [
                WorkflowStep(
                    step_id="update_market_learning",
                    name="Update Market Learning",
                    description="Update market learning from events",
                    execute_func=self.step_registry["update_market_learning"],
                    dependencies=[],
                    timeout=300
                ),
                WorkflowStep(
                    step_id="update_correlations",
                    name="Update Correlations",
                    description="Update correlation matrices",
                    execute_func=self.step_registry["update_correlations"],
                    dependencies=["update_market_learning"],
                    timeout=600
                )
            ]
        
        elif workflow_type == WorkflowType.RISK_ASSESSMENT:
            steps = [
                WorkflowStep(
                    step_id="assess_risk_events",
                    name="Assess Risk Events",
                    description="Assess and learn from risk events",
                    execute_func=self.step_registry["assess_risk_events"],
                    dependencies=[],
                    timeout=300
                )
            ]
        
        return steps
    
    async def _execute_workflow_async(self, 
                                     workflow_id: str,
                                     steps: List[WorkflowStep], 
                                     data: Dict[str, Any]) -> str:
        """Execute workflow asynchronously"""
        
        workflow_result = self.active_workflows[workflow_id]
        completed_steps = set()
        
        try:
            for step in steps:
                # Check dependencies
                if not all(dep in completed_steps for dep in step.dependencies):
                    logger.warning(f"Skipping step {step.step_id} - dependencies not met")
                    continue
                
                # Execute step
                logger.info(f"Executing step {step.step_id} in workflow {workflow_id}")
                
                try:
                    # Run step in thread pool
                    step_result = await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        step.execute_func,
                        data
                    )
                    
                    # Store step output
                    workflow_result.outputs[step.step_id] = step_result
                    completed_steps.add(step.step_id)
                    workflow_result.steps_completed.append(step.step_id)
                    
                    logger.info(f"Completed step {step.step_id}")
                    
                except Exception as e:
                    logger.error(f"Step {step.step_id} failed: {e}")
                    workflow_result.steps_failed.append(step.step_id)
                    workflow_result.errors.append(f"Step {step.step_id}: {str(e)}")
                    
                    if step.error_handling == "stop":
                        break
                    elif step.error_handling == "continue":
                        continue
                    elif step.error_handling == "retry":
                        # Implement retry logic
                        await self._retry_step(step, data, workflow_result)
        
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            workflow_result.errors.append(str(e))
        
        finally:
            # Mark workflow as completed or failed
            if workflow_result.steps_failed:
                workflow_result.status = WorkflowStatus.FAILED
            else:
                workflow_result.status = WorkflowStatus.COMPLETED
            workflow_result.end_time = datetime.now()
        
        return workflow_id
    
    async def _execute_workflow_sync(self, workflow_id: str, steps: List[WorkflowStep], data: Dict[str, Any]) -> str:
        """Execute workflow synchronously for high priority tasks"""
        return await self._execute_workflow_async(workflow_id, steps, data)
    
    async def _retry_step(self, step: WorkflowStep, data: Dict[str, Any], workflow_result: WorkflowResult):
        """Retry a failed step"""
        step.retry_count += 1
        
        if step.retry_count <= step.max_retries:
            logger.info(f"Retrying step {step.step_id} (attempt {step.retry_count})")
            try:
                step_result = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    step.execute_func,
                    data
                )
                workflow_result.outputs[step.step_id] = step_result
                workflow_result.steps_completed.append(step.step_id)
                logger.info(f"Successfully retried step {step.step_id}")
            except Exception as e:
                logger.error(f"Retry {step.retry_count} failed for step {step.step_id}: {e}")
                if step.retry_count == step.max_retries:
                    workflow_result.steps_failed.append(step.step_id)
                    workflow_result.errors.append(f"Step {step.step_id}: {str(e)}")
        else:
            workflow_result.steps_failed.append(step.step_id)
            workflow_result.errors.append(f"Step {step.step_id}: Max retries exceeded")
    
    # Workflow Step Implementations
    
    def _analyze_trade_outcome(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trade outcome and update memory"""
        
        trade_event = TradeEvent(**data.get("trade_event", {}))
        
        result = {
            "trade_analyzed": trade_event.trade_id,
            "outcome_classification": self._classify_outcome(trade_event),
            "performance_metrics": self._calculate_performance_metrics(trade_event),
            "memory_updates": []
        }
        
        # Create trade outcome memory block
        if trade_event.outcome:
            outcome_block = {
                "trade_id": trade_event.trade_id,
                "symbol": trade_event.symbol,
                "strategy": trade_event.strategy,
                "outcome": trade_event.outcome,
                "pnl": trade_event.pnl,
                "confidence": trade_event.confidence,
                "risk_metrics": trade_event.risk_metrics,
                "market_conditions": trade_event.market_conditions,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            result["memory_updates"].append(outcome_block)
        
        return result
    
    def _classify_outcome(self, trade_event: TradeEvent) -> str:
        """Classify trade outcome"""
        if trade_event.pnl is None:
            return "pending"
        
        if trade_event.pnl > 0:
            if trade_event.pnl > 0.02:  # >2% profit
                return "win"
            else:
                return "small_win"
        else:
            if trade_event.pnl < -0.02:  # <-2% loss
                return "loss"
            else:
                return "small_loss"
    
    def _calculate_performance_metrics(self, trade_event: TradeEvent) -> Dict[str, float]:
        """Calculate performance metrics from trade"""
        if trade_event.pnl is None:
            return {}
        
        return {
            "pnl": trade_event.pnl,
            "return_pct": trade_event.pnl / trade_event.entry_price if trade_event.entry_price > 0 else 0,
            "risk_reward_ratio": abs(trade_event.pnl / trade_event.risk_metrics.get("stop_loss", 0.01)),
            "confidence_weighted_return": trade_event.pnl * trade_event.confidence
        }
    
    def _update_strategy_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update strategy performance metrics"""
        
        strategy = data.get("strategy", "default")
        trade_data = data.get("trade_event", {})
        
        # Get existing performance data
        performance_blocks = self.memory_manager.search_memory_blocks(
            agent_id=data.get("agent_id"),
            block_type=MemoryBlockType.PERFORMANCE_METRICS,
            limit=10
        )
        
        # Update metrics
        result = {
            "strategy": strategy,
            "trades_analyzed": len(trade_data),
            "metrics_updated": True,
            "recommendations": []
        }
        
        # Generate recommendations based on performance
        if trade_data.get("outcome") == "loss":
            result["recommendations"].append("Review risk management parameters")
            result["recommendations"].append("Consider reducing position sizes")
        
        return result
    
    def _discover_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Discover new trading patterns from recent data"""
        
        # Get recent trade outcomes
        trade_blocks = self.memory_manager.search_memory_blocks(
            agent_id=data.get("agent_id"),
            block_type=MemoryBlockType.TRADE_OUTCOMES,
            limit=100
        )
        
        result = {
            "patterns_discovered": [],
            "confidence_scores": {},
            "recommendations": []
        }
        
        # Simple pattern discovery logic
        if len(trade_blocks) >= 10:
            # Group by symbol and strategy
            symbol_performance = {}
            
            for block in trade_blocks:
                if isinstance(block.content, dict):
                    symbol = block.content.get("symbol")
                    strategy = block.content.get("strategy")
                    
                    key = f"{symbol}_{strategy}"
                    if key not in symbol_performance:
                        symbol_performance[key] = []
                    
                    symbol_performance[key].append(block.content.get("outcome", "unknown"))
            
            # Identify winning patterns
            for key, outcomes in symbol_performance.items():
                if len(outcomes) >= 3:
                    win_rate = outcomes.count("win") / len(outcomes)
                    if win_rate >= 0.7:
                        symbol, strategy = key.split("_", 1)
                        result["patterns_discovered"].append({
                            "pattern_id": f"pattern_{key}",
                            "symbol": symbol,
                            "strategy": strategy,
                            "success_rate": win_rate,
                            "sample_size": len(outcomes)
                        })
        
        return result
    
    def _assess_risk_events(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess and learn from risk events"""
        
        risk_events = data.get("risk_events", [])
        
        result = {
            "events_assessed": len(risk_events),
            "lessons_learned": [],
            "policy_updates": []
        }
        
        for event in risk_events:
            # Analyze risk event
            if event.get("severity") == "high":
                result["lessons_learned"].append(f"High severity event: {event.get('event_type')}")
                result["policy_updates"].append("Strengthen risk management protocols")
        
        return result
    
    def _update_market_learning(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update market learning from market events"""
        
        market_events = data.get("market_events", [])
        
        result = {
            "events_processed": len(market_events),
            "learning_updates": [],
            "regime_observations": []
        }
        
        for event in market_events:
            # Create market learning entry
            learning = MarketLearning(
                learning_id=f"learn_{event.get('event_id')}",
                market_regime=event.get("market_conditions", {}).get("regime", "unknown"),
                adaptation_type="market_response",
                changes_made=event.get("learning_points", []),
                performance_impact=event.get("impact_metrics", {}).get("price_impact", 0),
                confidence=event.get("severity", "medium") == "high" and 0.8 or 0.5,
                rollback_data={}
            )
            
            result["learning_updates"].append({
                "learning_id": learning.learning_id,
                "market_regime": learning.market_regime,
                "adaptation_type": learning.adaptation_type
            })
        
        return result
    
    def _analyze_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall performance"""
        
        # Get performance insights
        insights = self.memory_manager.get_performance_insights(data.get("agent_id"))
        
        result = {
            "total_insights": len(insights),
            "high_priority_insights": len([i for i in insights if i.urgency == "high"]),
            "insight_types": list(set(i.insight_type for i in insights)),
            "recommendations": []
        }
        
        # Aggregate recommendations
        for insight in insights:
            result["recommendations"].extend(insight.recommendations)
        
        return result
    
    def _validate_predictions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate predictions made by agents"""
        
        predictions = data.get("predictions", [])
        
        result = {
            "predictions_validated": len(predictions),
            "accuracy_metrics": {},
            "learning_updates": []
        }
        
        # Calculate accuracy metrics
        if predictions:
            correct = sum(1 for p in predictions if p.get("outcome") == p.get("prediction"))
            accuracy = correct / len(predictions)
            
            result["accuracy_metrics"]["overall_accuracy"] = accuracy
            
            if accuracy < 0.6:
                result["learning_updates"].append("Prediction models need recalibration")
        
        return result
    
    def _generate_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable insights"""
        
        insights = self.memory_manager.get_performance_insights(data.get("agent_id"))
        
        result = {
            "insights_generated": len(insights),
            "urgent_actions": [],
            "strategic_recommendations": []
        }
        
        for insight in insights:
            if insight.urgency == "high":
                result["urgent_actions"].append({
                    "title": insight.title,
                    "description": insight.description,
                    "recommendations": insight.recommendations
                })
            else:
                result["strategic_recommendations"].append({
                    "title": insight.title,
                    "description": insight.description
                })
        
        return result
    
    def _update_correlations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update correlation matrices"""
        
        # Get recent market data
        market_blocks = self.memory_manager.search_memory_blocks(
            agent_id=data.get("agent_id"),
            block_type=MemoryBlockType.MARKET_CONDITIONS,
            limit=50
        )
        
        result = {
            "correlations_updated": len(market_blocks) > 0,
            "symbols_analyzed": [],
            "correlation_matrix": {}
        }
        
        # Extract symbols from market conditions
        for block in market_blocks:
            if isinstance(block.content, dict):
                symbols = block.content.get("symbols", [])
                result["symbols_analyzed"].extend(symbols)
        
        result["symbols_analyzed"] = list(set(result["symbols_analyzed"]))
        
        return result
    
    def _archive_old_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Archive old memory blocks"""
        
        # Optimize memory usage
        stats = self.memory_manager.optimize_memory_usage()
        
        result = {
            "archive_completed": True,
            "stats": stats
        }
        
        return result
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get workflow execution status"""
        return self.active_workflows.get(workflow_id)
    
    def get_active_workflows(self, agent_id: str = None) -> List[WorkflowResult]:
        """Get list of active workflows"""
        workflows = list(self.active_workflows.values())
        
        if agent_id:
            workflows = [w for w in workflows if agent_id in w.workflow_id]
        
        return workflows
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel active workflow"""
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].status = WorkflowStatus.CANCELLED
            self.active_workflows[workflow_id].end_time = datetime.now()
            return True
        return False


class WorkflowScheduler:
    """Schedules and manages workflow execution"""
    
    def __init__(self, workflow_executor: WorkflowExecutor):
        self.workflow_executor = workflow_executor
        self.scheduled_workflows = {}
        self.running = False
        self.scheduler_thread = None
    
    def start(self):
        """Start the workflow scheduler"""
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.start()
        logger.info("Workflow scheduler started")
    
    def stop(self):
        """Stop the workflow scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logger.info("Workflow scheduler stopped")
    
    def schedule_workflow(self, 
                         workflow_type: WorkflowType,
                         agent_id: str,
                         data: Dict[str, Any],
                         schedule_time: datetime,
                         recurring: bool = False,
                         interval_hours: int = 24) -> str:
        """Schedule a workflow for future execution"""
        
        schedule_id = f"sched_{workflow_type.value}_{agent_id}_{schedule_time.strftime('%Y%m%d_%H%M%S')}"
        
        self.scheduled_workflows[schedule_id] = {
            "workflow_type": workflow_type,
            "agent_id": agent_id,
            "data": data,
            "schedule_time": schedule_time,
            "recurring": recurring,
            "interval_hours": interval_hours,
            "last_execution": None,
            "execution_count": 0
        }
        
        logger.info(f"Scheduled workflow {schedule_id} for {schedule_time}")
        return schedule_id
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for schedule_id, schedule_info in list(self.scheduled_workflows.items()):
                    if current_time >= schedule_info["schedule_time"]:
                        # Execute workflow
                        asyncio.run(
                            self.workflow_executor.execute_workflow(
                                schedule_info["workflow_type"],
                                schedule_info["agent_id"],
                                schedule_info["data"]
                            )
                        )
                        
                        schedule_info["last_execution"] = current_time
                        schedule_info["execution_count"] += 1
                        
                        # Handle recurring schedules
                        if schedule_info["recurring"]:
                            schedule_info["schedule_time"] = current_time + timedelta(hours=schedule_info["interval_hours"])
                        else:
                            # Remove non-recurring workflow
                            del self.scheduled_workflows[schedule_id]
                
                # Sleep for 30 seconds before next check
                threading.Event().wait(30)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                threading.Event().wait(60)  # Wait longer on error
    
    def get_scheduled_workflows(self) -> Dict[str, Any]:
        """Get all scheduled workflows"""
        return self.scheduled_workflows
    
    def cancel_scheduled_workflow(self, schedule_id: str) -> bool:
        """Cancel a scheduled workflow"""
        if schedule_id in self.scheduled_workflows:
            del self.scheduled_workflows[schedule_id]
            return True
        return False


# Utility functions for workflow data preparation

def prepare_trade_analysis_workflow(agent_id: str, trade_event: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare data for trade analysis workflow"""
    return {
        "agent_id": agent_id,
        "trade_event": trade_event,
        "workflow_type": WorkflowType.TRADE_ANALYSIS
    }


def prepare_performance_review_workflow(agent_id: str, time_period: str = "daily") -> Dict[str, Any]:
    """Prepare data for performance review workflow"""
    return {
        "agent_id": agent_id,
        "time_period": time_period,
        "workflow_type": WorkflowType.PERFORMANCE_REVIEW
    }


def prepare_market_learning_workflow(agent_id: str, market_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare data for market learning workflow"""
    return {
        "agent_id": agent_id,
        "market_events": market_events,
        "workflow_type": WorkflowType.MARKET_LEARNING
    }


def prepare_strategy_evolution_workflow(agent_id: str) -> Dict[str, Any]:
    """Prepare data for strategy evolution workflow"""
    return {
        "agent_id": agent_id,
        "workflow_type": WorkflowType.STRATEGY_EVOLUTION
    }


def prepare_risk_assessment_workflow(agent_id: str, risk_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare data for risk assessment workflow"""
    return {
        "agent_id": agent_id,
        "risk_events": risk_events,
        "workflow_type": WorkflowType.RISK_ASSESSMENT
    }