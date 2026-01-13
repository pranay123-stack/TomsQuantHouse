#!/usr/bin/env python3
"""
Trading Workflows and Insights Module for Letta API

Provides automated trading workflows, agent memory updates for trading insights,
and intelligent analysis of trading patterns and market conditions.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import statistics
import numpy as np
import pandas as pd

from letta_client import (
    LettaAPIClient, MemoryBlockType, Priority, 
    TradingPattern, TradeEvent, AgentRole
)
from memory_manager import AdvancedMemoryManager, create_memory_manager

logger = logging.getLogger(__name__)


class WorkflowType(Enum):
    """Types of trading workflows"""
    TRADE_ANALYSIS = "trade_analysis"
    STRATEGY_EVOLUTION = "strategy_evolution"
    RISK_ASSESSMENT = "risk_assessment"
    MARKET_LEARNING = "market_learning"
    PERFORMANCE_REVIEW = "performance_review"
    PATTERN_DISCOVERY = "pattern_discovery"
    OPPORTUNITY_IDENTIFICATION = "opportunity_identification"
    REGIME_DETECTION = "regime_detection"


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MarketRegime(Enum):
    """Market regime types"""
    BULL_TRENDING = "bull_trending"
    BEAR_TRENDING = "bear_trending"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"


@dataclass
class WorkflowExecution:
    """Workflow execution record"""
    workflow_id: str
    workflow_type: WorkflowType
    agent_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    input_data: Dict[str, Any] = None
    output_data: Dict[str, Any] = None
    errors: List[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class PerformanceInsight:
    """Performance analysis insight"""
    title: str
    description: str
    insight_type: str
    confidence: float
    impact_score: float
    actionable_recommendations: List[str]
    supporting_data: Dict[str, Any]
    time_period: str
    created_at: datetime


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_level: RiskLevel
    risk_score: float
    key_risks: List[str]
    risk_factors: Dict[str, Any]
    mitigation_strategies: List[str]
    confidence: float
    assessment_date: datetime


@dataclass
class MarketCondition:
    """Market condition analysis"""
    regime: MarketRegime
    confidence: float
    volatility: float
    trend_direction: str
    key_indicators: Dict[str, Any]
    market_sentiment: str
    timeframe: str
    analysis_date: datetime


@dataclass
class StrategyEvolution:
    """Strategy evolution recommendation"""
    strategy_name: str
    current_performance: float
    recommended_changes: List[str]
    performance_projections: Dict[str, float]
    implementation_priority: str
    expected_improvement: float
    risk_considerations: List[str]


class TradingWorkflows:
    """
    Trading Workflows Engine for automated trading analysis and insights
    
    Features:
    - Automated trade analysis workflows
    - Strategy evolution and optimization
    - Risk assessment and monitoring
    - Market learning and regime detection
    - Performance review and insights
    - Pattern discovery and validation
    """
    
    def __init__(self, client: LettaAPIClient):
        self.client = client
        self.memory_manager = create_memory_manager(client)
        self._workflow_history = []
        self._schedule_tasks = {}  # For scheduled workflows
        
    # === WORKFLOW EXECUTION ===
    
    def execute_trade_analysis_workflow(
        self,
        agent_id: str,
        trade_event: TradeEvent,
        include_pattern_update: bool = True
    ) -> str:
        """
        Execute comprehensive trade analysis workflow
        
        Analyzes trade outcome, updates patterns, assesses performance,
        and generates insights for strategy improvement.
        """
        
        workflow_id = f"trade_analysis_{trade_event.trade_id}_{int(datetime.now().timestamp())}"
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.TRADE_ANALYSIS,
            agent_id=agent_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
            input_data=asdict(trade_event)
        )
        
        try:
            logger.info(f"Starting trade analysis workflow: {workflow_id}")
            
            # 1. Record trade outcome
            self.client.record_trade_outcome(agent_id, trade_event)
            
            # 2. Update trading patterns based on trade outcome
            if include_pattern_update:
                self._update_patterns_from_trade(agent_id, trade_event)
            
            # 3. Generate performance insights
            performance_insights = self._analyze_trade_performance(agent_id, trade_event)
            
            # 4. Assess risk implications
            risk_assessment = self._assess_trade_risk(agent_id, trade_event)
            
            # 5. Generate market context updates
            market_context = self._update_market_context(agent_id, trade_event)
            
            # 6. Store workflow results
            workflow.output_data = {
                "performance_insights": [asdict(insight) for insight in performance_insights],
                "risk_assessment": asdict(risk_assessment),
                "market_context": asdict(market_context),
                "pattern_updates": self._get_recent_pattern_updates(agent_id)
            }
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            
            logger.info(f"Trade analysis workflow completed: {workflow_id}")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.errors = [str(e)]
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            logger.error(f"Trade analysis workflow failed: {workflow_id} - {e}")
        
        self._workflow_history.append(workflow)
        return workflow_id
    
    def execute_strategy_evolution_workflow(
        self,
        agent_id: str,
        analysis_period_days: int = 30
    ) -> str:
        """
        Execute strategy evolution workflow
        
        Analyzes strategy performance over time, identifies improvement opportunities,
        and generates evolution recommendations.
        """
        
        workflow_id = f"strategy_evolution_{agent_id}_{int(datetime.now().timestamp())}"
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.STRATEGY_EVOLUTION,
            agent_id=agent_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
            input_data={"analysis_period_days": analysis_period_days}
        )
        
        try:
            logger.info(f"Starting strategy evolution workflow: {workflow_id}")
            
            # 1. Get historical trade data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=analysis_period_days)
            
            trade_outcomes = self._get_trade_outcomes_in_period(agent_id, start_date, end_date)
            
            # 2. Analyze strategy performance
            strategy_performance = self._analyze_strategy_performance(trade_outcomes)
            
            # 3. Identify underperforming strategies
            underperformers = self._identify_underperforming_strategies(strategy_performance)
            
            # 4. Generate evolution recommendations
            evolution_recommendations = self._generate_strategy_recommendations(
                strategy_performance, underperformers
            )
            
            # 5. Update strategy memory
            self._update_strategy_memory(agent_id, evolution_recommendations)
            
            # 6. Create performance report
            performance_report = self._create_performance_report(strategy_performance)
            
            workflow.output_data = {
                "strategy_performance": strategy_performance,
                "underperforming_strategies": underperformers,
                "evolution_recommendations": [asdict(rec) for rec in evolution_recommendations],
                "performance_report": performance_report,
                "analysis_period_days": analysis_period_days
            }
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            
            logger.info(f"Strategy evolution workflow completed: {workflow_id}")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.errors = [str(e)]
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            logger.error(f"Strategy evolution workflow failed: {workflow_id} - {e}")
        
        self._workflow_history.append(workflow)
        return workflow_id
    
    def execute_risk_assessment_workflow(
        self,
        agent_id: str,
        risk_focus: str = "comprehensive"
    ) -> str:
        """
        Execute risk assessment workflow
        
        Analyzes current risk exposure, identifies potential risk events,
        and generates risk management recommendations.
        """
        
        workflow_id = f"risk_assessment_{agent_id}_{int(datetime.now().timestamp())}"
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.RISK_ASSESSMENT,
            agent_id=agent_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
            input_data={"risk_focus": risk_focus}
        )
        
        try:
            logger.info(f"Starting risk assessment workflow: {workflow_id}")
            
            # 1. Get current portfolio exposure
            portfolio_exposure = self._analyze_portfolio_exposure(agent_id)
            
            # 2. Analyze recent risk events
            recent_risk_events = self._analyze_recent_risk_events(agent_id)
            
            # 3. Assess market risk factors
            market_risk_factors = self._assess_market_risk_factors(agent_id)
            
            # 4. Generate risk metrics
            risk_metrics = self._calculate_risk_metrics(agent_id)
            
            # 5. Identify risk mitigation opportunities
            mitigation_strategies = self._identify_risk_mitigation_strategies(
                portfolio_exposure, market_risk_factors, risk_metrics
            )
            
            # 6. Create comprehensive risk assessment
            risk_assessment = RiskAssessment(
                risk_level=self._determine_overall_risk_level(risk_metrics),
                risk_score=self._calculate_overall_risk_score(risk_metrics),
                key_risks=self._identify_key_risks(risk_metrics, market_risk_factors),
                risk_factors={
                    "portfolio_exposure": portfolio_exposure,
                    "market_factors": market_risk_factors,
                    "risk_metrics": risk_metrics,
                    "recent_events": recent_risk_events
                },
                mitigation_strategies=mitigation_strategies,
                confidence=0.85,
                assessment_date=datetime.now()
            )
            
            # 7. Update risk memory
            self._update_risk_memory(agent_id, risk_assessment)
            
            workflow.output_data = {
                "risk_assessment": asdict(risk_assessment),
                "risk_focus": risk_focus,
                "mitigation_strategies": mitigation_strategies
            }
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            
            logger.info(f"Risk assessment workflow completed: {workflow_id}")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.errors = [str(e)]
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            logger.error(f"Risk assessment workflow failed: {workflow_id} - {e}")
        
        self._workflow_history.append(workflow)
        return workflow_id
    
    def execute_market_learning_workflow(
        self,
        agent_id: str,
        lookback_days: int = 7
    ) -> str:
        """
        Execute market learning workflow
        
        Analyzes recent market conditions, identifies patterns and regimes,
        and updates market knowledge.
        """
        
        workflow_id = f"market_learning_{agent_id}_{int(datetime.now().timestamp())}"
        workflow = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.MARKET_LEARNING,
            agent_id=agent_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now(),
            input_data={"lookback_days": lookback_days}
        )
        
        try:
            logger.info(f"Starting market learning workflow: {workflow_id}")
            
            # 1. Analyze recent market conditions
            market_conditions = self._analyze_recent_market_conditions(agent_id, lookback_days)
            
            # 2. Detect market regime
            regime_detection = self._detect_market_regime(market_conditions)
            
            # 3. Identify market patterns
            market_patterns = self._identify_market_patterns(agent_id, lookback_days)
            
            # 4. Update market memory
            self._update_market_memory(agent_id, market_conditions, regime_detection)
            
            # 5. Generate market insights
            market_insights = self._generate_market_insights(market_conditions, regime_detection)
            
            workflow.output_data = {
                "market_conditions": asdict(market_conditions),
                "regime_detection": asdict(regime_detection),
                "market_patterns": market_patterns,
                "market_insights": [asdict(insight) for insight in market_insights],
                "lookback_days": lookback_days
            }
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            
            logger.info(f"Market learning workflow completed: {workflow_id}")
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.errors = [str(e)]
            workflow.completed_at = datetime.now()
            workflow.duration_seconds = (workflow.completed_at - workflow.started_at).total_seconds()
            logger.error(f"Market learning workflow failed: {workflow_id} - {e}")
        
        self._workflow_history.append(workflow)
        return workflow_id
    
    # === PATTERN MANAGEMENT ===
    
    def discover_new_patterns(
        self,
        agent_id: str,
        symbol: str,
        analysis_period_days: int = 30
    ) -> List[TradingPattern]:
        """
        Discover new trading patterns from historical data
        
        Analyzes trade outcomes to identify new patterns with statistical significance.
        """
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=analysis_period_days)
        
        # Get trade outcomes for the symbol
        trade_outcomes = self._get_trade_outcomes_in_period(agent_id, start_date, end_date, symbol)
        
        if len(trade_outcomes) < 5:
            logger.warning(f"Insufficient trade data for pattern discovery: {len(trade_outcomes)} trades")
            return []
        
        discovered_patterns = []
        
        # Analyze price action patterns
        price_patterns = self._analyze_price_action_patterns(trade_outcomes)
        
        # Analyze volume patterns
        volume_patterns = self._analyze_volume_patterns(trade_outcomes)
        
        # Analyze time-based patterns
        time_patterns = self._analyze_time_based_patterns(trade_outcomes)
        
        # Combine and validate patterns
        all_patterns = price_patterns + volume_patterns + time_patterns
        
        for pattern_data in all_patterns:
            if pattern_data["success_rate"] >= 0.6 and pattern_data["sample_size"] >= 3:
                # Create trading pattern
                pattern_id = self.client.create_trading_pattern(
                    agent_id=agent_id,
                    symbol=symbol,
                    pattern_type=pattern_data["pattern_type"],
                    success_rate=pattern_data["success_rate"],
                    confidence=pattern_data["confidence"],
                    conditions=pattern_data["conditions"],
                    entry_signals=pattern_data["entry_signals"],
                    exit_signals=pattern_data["exit_signals"],
                    risk_metrics=pattern_data["risk_metrics"]
                )
                
                if pattern_id:
                    pattern = TradingPattern(
                        id=pattern_id,
                        symbol=symbol,
                        pattern_type=pattern_data["pattern_type"],
                        success_rate=pattern_data["success_rate"],
                        confidence=pattern_data["confidence"],
                        conditions=pattern_data["conditions"],
                        entry_signals=pattern_data["entry_signals"],
                        exit_signals=pattern_data["exit_signals"],
                        risk_metrics=pattern_data["risk_metrics"],
                        performance_history=[],
                        created_at=datetime.now()
                    )
                    discovered_patterns.append(pattern)
        
        logger.info(f"Discovered {len(discovered_patterns)} new patterns for {symbol}")
        return discovered_patterns
    
    def validate_existing_patterns(self, agent_id: str) -> Dict[str, Any]:
        """
        Validate existing trading patterns against recent performance
        
        Tests pattern effectiveness and identifies patterns that need updating or removal.
        """
        
        patterns = self.client.get_trading_patterns(agent_id)
        validation_results = {
            "validated_patterns": [],
            "patterns_to_update": [],
            "patterns_to_remove": [],
            "validation_date": datetime.now().isoformat()
        }
        
        for pattern in patterns:
            # Get recent performance for this pattern
            recent_performance = self._get_pattern_performance(agent_id, pattern.id, days=30)
            
            if recent_performance["sample_size"] >= 3:
                current_success_rate = recent_performance["success_rate"]
                original_success_rate = pattern.success_rate
                
                # Determine pattern status
                if current_success_rate >= original_success_rate * 0.8:  # 80% of original performance
                    validation_results["validated_patterns"].append({
                        "pattern_id": pattern.id,
                        "pattern_type": pattern.pattern_type,
                        "current_success_rate": current_success_rate,
                        "original_success_rate": original_success_rate,
                        "status": "validated"
                    })
                
                elif current_success_rate >= original_success_rate * 0.5:  # 50-80% of original
                    validation_results["patterns_to_update"].append({
                        "pattern_id": pattern.id,
                        "pattern_type": pattern.pattern_type,
                        "current_success_rate": current_success_rate,
                        "original_success_rate": original_success_rate,
                        "performance_decline": (original_success_rate - current_success_rate) / original_success_rate,
                        "recommended_action": "update_conditions"
                    })
                
                else:  # Less than 50% of original performance
                    validation_results["patterns_to_remove"].append({
                        "pattern_id": pattern.id,
                        "pattern_type": pattern.pattern_type,
                        "current_success_rate": current_success_rate,
                        "original_success_rate": original_success_rate,
                        "performance_decline": (original_success_rate - current_success_rate) / original_success_rate,
                        "recommended_action": "remove_pattern"
                    })
        
        # Store validation results in memory
        validation_block_id = self.client.add_memory_block(
            agent_id=agent_id,
            block_type=MemoryBlockType.PERFORMANCE_METRICS,
            title=f"Pattern Validation Results - {datetime.now().strftime('%Y-%m-%d')}",
            content=json.dumps(validation_results, indent=2),
            metadata={
                "validation_type": "pattern_performance",
                "validated_count": len(validation_results["validated_patterns"]),
                "update_needed": len(validation_results["patterns_to_update"]),
                "removal_needed": len(validation_results["patterns_to_remove"])
            },
            tags=["validation", "patterns", "performance"],
            priority=Priority.MEDIUM
        )
        
        return validation_results
    
    # === PERFORMANCE ANALYSIS ===
    
    def get_comprehensive_performance_analysis(
        self,
        agent_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance analysis for an agent
        
        Includes win rate, profit factor, drawdown analysis, and strategic insights.
        """
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get trade outcomes
        trade_outcomes = self._get_trade_outcomes_in_period(agent_id, start_date, end_date)
        
        if not trade_outcomes:
            return {"error": "No trade outcomes found for the specified period"}
        
        # Convert to DataFrame for analysis
        trades_df = pd.DataFrame([asdict(trade) for trade in trade_outcomes])
        
        # Basic performance metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['outcome'] == 'win'])
        losing_trades = len(trades_df[trades_df['outcome'] == 'loss'])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Profit metrics
        total_pnl = trades_df['pnl'].sum()
        avg_win = trades_df[trades_df['outcome'] == 'win']['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['outcome'] == 'loss']['pnl'].mean() if losing_trades > 0 else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # Risk metrics
        max_drawdown = self._calculate_max_drawdown(trades_df['pnl'])
        volatility = trades_df['pnl'].std()
        sharpe_ratio = (trades_df['pnl'].mean() / trades_df['pnl'].std()) if trades_df['pnl'].std() > 0 else 0
        
        # Strategy performance breakdown
        strategy_performance = trades_df.groupby('strategy').agg({
            'pnl': ['count', 'sum', 'mean', 'std'],
            'outcome': lambda x: (x == 'win').sum() / len(x)
        }).round(4)
        
        # Time-based analysis
        trades_df['hour'] = pd.to_datetime(trades_df['timestamp']).dt.hour
        hourly_performance = trades_df.groupby('hour')['pnl'].mean().to_dict()
        
        trades_df['day_of_week'] = pd.to_datetime(trades_df['timestamp']).dt.dayofweek
        daily_performance = trades_df.groupby('day_of_week')['pnl'].mean().to_dict()
        
        # Performance insights
        insights = self._generate_performance_insights(trades_df, win_rate, profit_factor, max_drawdown)
        
        return {
            "period_days": period_days,
            "basic_metrics": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "average_win": avg_win,
                "average_loss": avg_loss,
                "profit_factor": profit_factor
            },
            "risk_metrics": {
                "max_drawdown": max_drawdown,
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio
            },
            "strategy_breakdown": strategy_performance.to_dict(),
            "temporal_analysis": {
                "hourly_performance": hourly_performance,
                "daily_performance": daily_performance
            },
            "performance_insights": [asdict(insight) for insight in insights],
            "analysis_date": datetime.now().isoformat()
        }
    
    # === MARKET CONTEXT ===
    
    def get_market_context_analysis(self, agent_id: str) -> Dict[str, Any]:
        """
        Get comprehensive market context analysis
        
        Analyzes current market conditions, regime, and provides context for trading decisions.
        """
        
        # Get market conditions from memory
        market_conditions_blocks = self.client.search_memory(
            agent_id=agent_id,
            query="market conditions regime",
            query_type=QueryType.SEMANTIC_SIMILARITY,
            filters={"block_type": "market_regime"},
            limit=5
        )
        
        # Get recent volatility data
        volatility_blocks = self.client.search_memory(
            agent_id=agent_id,
            query="volatility",
            query_type=QueryType.TEXT_SEARCH,
            filters={"block_type": "market_conditions"},
            limit=3
        )
        
        # Get correlation data
        correlation_blocks = self.client.search_memory(
            agent_id=agent_id,
            query="correlation",
            query_type=QueryType.TEXT_SEARCH,
            filters={"block_type": "correlation_matrices"},
            limit=3
        )
        
        # Analyze market sentiment from recent trades
        recent_trades = self._get_recent_trades(agent_id, days=7)
        
        # Determine current market regime
        current_regime = self._determine_current_market_regime(market_conditions_blocks, recent_trades)
        
        # Calculate market metrics
        market_metrics = self._calculate_market_metrics(volatility_blocks, correlation_blocks)
        
        # Generate market insights
        market_insights = self._generate_market_insights_from_context(
            current_regime, market_metrics, recent_trades
        )
        
        return {
            "current_regime": asdict(current_regime),
            "market_metrics": market_metrics,
            "market_insights": market_insights,
            "context_sources": {
                "market_conditions_blocks": len(market_conditions_blocks),
                "volatility_blocks": len(volatility_blocks),
                "correlation_blocks": len(correlation_blocks),
                "recent_trades": len(recent_trades)
            },
            "analysis_date": datetime.now().isoformat()
        }
    
    # === HELPER METHODS ===
    
    def _update_patterns_from_trade(self, agent_id: str, trade_event: TradeEvent):
        """Update trading patterns based on trade outcome"""
        
        # Find relevant patterns for this trade
        relevant_patterns = self.client.get_trading_patterns(
            agent_id=agent_id,
            symbol=trade_event.symbol
        )
        
        for pattern in relevant_patterns:
            # Update pattern performance history
            performance_entry = {
                "trade_id": trade_event.trade_id,
                "timestamp": trade_event.timestamp.isoformat(),
                "outcome": trade_event.outcome,
                "pnl": trade_event.pnl,
                "exit_price": trade_event.exit_price
            }
            
            # Update pattern in memory (would need server support for partial updates)
            # For now, we create a new performance tracking block
            performance_block_id = self.client.add_memory_block(
                agent_id=agent_id,
                block_type=MemoryBlockType.PERFORMANCE_METRICS,
                title=f"Pattern Performance: {pattern.pattern_type} - {trade_event.trade_id}",
                content=json.dumps({
                    "pattern_id": pattern.id,
                    "pattern_type": pattern.pattern_type,
                    "performance_entry": performance_entry
                }, indent=2),
                metadata={
                    "pattern_id": pattern.id,
                    "trade_outcome": trade_event.outcome,
                    "recorded_by": "workflow_engine"
                },
                tags=["pattern", "performance", pattern.pattern_type.lower()],
                priority=Priority.MEDIUM
            )
    
    def _analyze_trade_performance(self, agent_id: str, trade_event: TradeEvent) -> List[PerformanceInsight]:
        """Analyze trade performance and generate insights"""
        
        insights = []
        
        # Analyze trade outcome
        if trade_event.outcome == "win":
            if trade_event.pnl > 0:
                insights.append(PerformanceInsight(
                    title="Profitable Trade Executed",
                    description=f"Successful {trade_event.strategy} trade on {trade_event.symbol} with {trade_event.pnl:.2f} PnL",
                    insight_type="performance",
                    confidence=0.9,
                    impact_score=0.7,
                    actionable_recommendations=[
                        f"Consider increasing position size for similar {trade_event.strategy} setups",
                        f"Document successful pattern conditions for {trade_event.symbol}"
                    ],
                    supporting_data={
                        "pnl": trade_event.pnl,
                        "strategy": trade_event.strategy,
                        "symbol": trade_event.symbol
                    },
                    time_period="single_trade",
                    created_at=datetime.now()
                ))
        
        # Analyze risk-reward
        if trade_event.exit_price and trade_event.entry_price:
            risk_reward = abs(trade_event.pnl) / (trade_event.entry_price * 0.02)  # Assuming 2% risk
            if risk_reward > 2.0:
                insights.append(PerformanceInsight(
                    title="Good Risk-Reward Trade",
                    description=f"Trade achieved {risk_reward:.1f}:1 risk-reward ratio",
                    insight_type="risk_management",
                    confidence=0.85,
                    impact_score=0.6,
                    actionable_recommendations=[
                        "Maintain similar risk-reward discipline",
                        "Use this as benchmark for future trades"
                    ],
                    supporting_data={"risk_reward_ratio": risk_reward},
                    time_period="single_trade",
                    created_at=datetime.now()
                ))
        
        return insights
    
    def _assess_trade_risk(self, agent_id: str, trade_event: TradeEvent) -> RiskAssessment:
        """Assess risk implications of a trade"""
        
        risk_score = 0.0
        key_risks = []
        
        # Position size risk
        if abs(trade_event.pnl) / trade_event.entry_price > 0.05:  # > 5% of entry price
            risk_score += 0.3
            key_risks.append("Large position size relative to account")
        
        # Strategy confidence risk
        if trade_event.confidence < 0.6:
            risk_score += 0.2
            key_risks.append("Low confidence trade execution")
        
        # Loss magnitude
        if trade_event.pnl < -100:  # Significant loss
            risk_score += 0.4
            key_risks.append("Significant loss magnitude")
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            key_risks=key_risks,
            risk_factors={
                "trade_event": asdict(trade_event),
                "position_size": abs(trade_event.pnl) / trade_event.entry_price,
                "confidence_level": trade_event.confidence
            },
            mitigation_strategies=self._get_risk_mitigation_strategies(trade_event, risk_score),
            confidence=0.8,
            assessment_date=datetime.now()
        )
    
    def _get_trade_outcomes_in_period(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime,
        symbol: Optional[str] = None
    ) -> List[TradeEvent]:
        """Get trade outcomes within a specific time period"""
        
        # Search for trade outcome blocks
        search_results = self.client.search_memory(
            agent_id=agent_id,
            query="trade outcome",
            query_type=QueryType.TEMPORAL_FILTER,
            filters={
                "block_type": "trade_outcomes",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            limit=1000
        )
        
        trade_events = []
        for result in search_results:
            try:
                trade_data = json.loads(result.content)
                trade_event = TradeEvent(**trade_data)
                
                # Filter by symbol if specified
                if symbol and trade_event.symbol != symbol:
                    continue
                
                trade_events.append(trade_event)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse trade outcome: {e}")
                continue
        
        return trade_events
    
    def _calculate_max_drawdown(self, pnl_series: pd.Series) -> float:
        """Calculate maximum drawdown from PnL series"""
        cumulative = pnl_series.cumsum()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _determine_current_market_regime(
        self,
        market_conditions_blocks: List,
        recent_trades: List
    ) -> MarketCondition:
        """Determine current market regime from available data"""
        
        # Simplified regime detection logic
        # In a real implementation, this would use more sophisticated analysis
        
        if not recent_trades:
            return MarketCondition(
                regime=MarketRegime.SIDEWAYS,
                confidence=0.5,
                volatility=0.0,
                trend_direction="unknown",
                key_indicators={},
                market_sentiment="neutral",
                timeframe="current",
                analysis_date=datetime.now()
            )
        
        # Analyze recent trade performance
        recent_pnl = [trade.pnl for trade in recent_trades if trade.pnl is not None]
        
        if not recent_pnl:
            return MarketCondition(
                regime=MarketRegime.SIDEWAYS,
                confidence=0.5,
                volatility=0.0,
                trend_direction="unknown",
                key_indicators={},
                market_sentiment="neutral",
                timeframe="current",
                analysis_date=datetime.now()
            )
        
        avg_pnl = statistics.mean(recent_pnl)
        pnl_volatility = statistics.stdev(recent_pnl) if len(recent_pnl) > 1 else 0
        
        # Simple regime classification
        if avg_pnl > 0 and pnl_volatility < 50:
            regime = MarketRegime.BULL_TRENDING
            trend_direction = "bullish"
            market_sentiment = "positive"
        elif avg_pnl < 0 and pnl_volatility > 50:
            regime = MarketRegime.BEAR_TRENDING
            trend_direction = "bearish"
            market_sentiment = "negative"
        elif pnl_volatility > 75:
            regime = MarketRegime.HIGH_VOLATILITY
            trend_direction = "volatile"
            market_sentiment = "uncertain"
        else:
            regime = MarketRegime.SIDEWAYS
            trend_direction = "sideways"
            market_sentiment = "neutral"
        
        return MarketCondition(
            regime=regime,
            confidence=0.7,
            volatility=pnl_volatility,
            trend_direction=trend_direction,
            key_indicators={
                "average_pnl": avg_pnl,
                "volatility": pnl_volatility,
                "sample_size": len(recent_pnl)
            },
            market_sentiment=market_sentiment,
            timeframe="current",
            analysis_date=datetime.now()
        )
    
    def _get_recent_trades(self, agent_id: str, days: int = 7) -> List[TradeEvent]:
        """Get recent trades for analysis"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self._get_trade_outcomes_in_period(agent_id, start_date, end_date)
    
    def _generate_performance_insights(
        self,
        trades_df: pd.DataFrame,
        win_rate: float,
        profit_factor: float,
        max_drawdown: float
    ) -> List[PerformanceInsight]:
        """Generate performance insights from trade analysis"""
        
        insights = []
        
        # Win rate insights
        if win_rate > 0.6:
            insights.append(PerformanceInsight(
                title="High Win Rate Performance",
                description=f"Win rate of {win_rate:.1%} indicates strong market timing",
                insight_type="performance",
                confidence=0.9,
                impact_score=0.8,
                actionable_recommendations=[
                    "Consider increasing position sizes",
                    "Document successful entry/exit criteria"
                ],
                supporting_data={"win_rate": win_rate},
                time_period="analysis_period",
                created_at=datetime.now()
            ))
        elif win_rate < 0.4:
            insights.append(PerformanceInsight(
                title="Low Win Rate Alert",
                description=f"Win rate of {win_rate:.1%} suggests strategy refinement needed",
                insight_type="performance",
                confidence=0.9,
                impact_score=0.9,
                actionable_recommendations=[
                    "Review entry criteria",
                    "Improve risk management",
                    "Analyze losing trades for patterns"
                ],
                supporting_data={"win_rate": win_rate},
                time_period="analysis_period",
                created_at=datetime.now()
            ))
        
        # Profit factor insights
        if profit_factor > 1.5:
            insights.append(PerformanceInsight(
                title="Strong Profit Factor",
                description=f"Profit factor of {profit_factor:.2f} shows excellent risk-reward balance",
                insight_type="risk_management",
                confidence=0.85,
                impact_score=0.7,
                actionable_recommendations=[
                    "Maintain current risk management approach",
                    "Consider scaling successful strategies"
                ],
                supporting_data={"profit_factor": profit_factor},
                time_period="analysis_period",
                created_at=datetime.now()
            ))
        
        # Drawdown insights
        if max_drawdown < -0.1:  # 10% drawdown
            insights.append(PerformanceInsight(
                title="High Drawdown Detected",
                description=f"Maximum drawdown of {max_drawdown:.1%} requires attention",
                insight_type="risk_management",
                confidence=0.9,
                impact_score=0.9,
                actionable_recommendations=[
                    "Implement stricter position sizing",
                    "Add stop-loss mechanisms",
                    "Reduce exposure during adverse conditions"
                ],
                supporting_data={"max_drawdown": max_drawdown},
                time_period="analysis_period",
                created_at=datetime.now()
            ))
        
        return insights
    
    def _get_risk_mitigation_strategies(self, trade_event: TradeEvent, risk_score: float) -> List[str]:
        """Get risk mitigation strategies for a trade"""
        
        strategies = []
        
        if risk_score > 0.5:
            strategies.extend([
                "Implement stricter position sizing",
                "Use stop-loss orders",
                "Diversify across multiple strategies"
            ])
        
        if trade_event.confidence < 0.7:
            strategies.append("Reduce position size for low-confidence trades")
        
        if abs(trade_event.pnl) / trade_event.entry_price > 0.03:
            strategies.append("Consider partial profit taking")
        
        return strategies
    
    # Additional helper methods would be implemented here...
    # For brevity, I'm showing the key structure. In a full implementation,
    # you would add more helper methods for:
    # - _analyze_portfolio_exposure
    # - _assess_market_risk_factors
    # - _calculate_risk_metrics
    # - _identify_risk_mitigation_strategies
    # - _update_market_memory
    # - And many more...
    
    # === UTILITY METHODS ===
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get status of a specific workflow"""
        for workflow in self._workflow_history:
            if workflow.workflow_id == workflow_id:
                return workflow
        return None
    
    def get_workflow_history(self, agent_id: Optional[str] = None, limit: int = 10) -> List[WorkflowExecution]:
        """Get workflow execution history"""
        workflows = self._workflow_history
        
        if agent_id:
            workflows = [w for w in workflows if w.agent_id == agent_id]
        
        return sorted(workflows, key=lambda x: x.started_at, reverse=True)[:limit]
    
    def get_performance_dashboard_data(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive data for performance dashboard"""
        
        # Get recent performance analysis
        performance_analysis = self.get_comprehensive_performance_analysis(agent_id, period_days=30)
        
        # Get market context
        market_context = self.get_market_context_analysis(agent_id)
        
        # Get recent workflows
        recent_workflows = self.get_workflow_history(agent_id, limit=5)
        
        # Get active patterns
        active_patterns = self.client.get_trading_patterns(agent_id)
        
        return {
            "performance_analysis": performance_analysis,
            "market_context": market_context,
            "recent_workflows": [asdict(w) for w in recent_workflows],
            "active_patterns_count": len(active_patterns),
            "dashboard_updated": datetime.now().isoformat()
        }


# === CONVENIENT FUNCTIONS ===

def create_trading_workflows(client: LettaAPIClient) -> TradingWorkflows:
    """Create a trading workflows instance"""
    return TradingWorkflows(client)


if __name__ == "__main__":
    # Example usage
    import sys
    sys.path.append('/workspace/code/letta_api')
    
    from letta_client import LettaAPIClient
    
    # Configuration
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8283"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "your-secret-api-key"
    agent_id = sys.argv[3] if len(sys.argv) > 3 else "test_agent"
    
    print("Trading Workflows Demo")
    print("=" * 50)
    
    client = LettaAPIClient(base_url, api_key)
    workflows = TradingWorkflows(client)
    
    try:
        # Simulate a trade event
        trade_event = TradeEvent(
            trade_id="demo_trade_001",
            symbol="AAPL",
            action="buy",
            quantity=100,
            entry_price=150.00,
            exit_price=155.50,
            pnl=5.50,
            strategy="bullish_breakout",
            confidence=0.8,
            outcome="win",
            timestamp=datetime.now(),
            metadata={}
        )
        
        # Execute trade analysis workflow
        print("1. Executing Trade Analysis Workflow:")
        workflow_id = workflows.execute_trade_analysis_workflow(agent_id, trade_event)
        print(f"   Workflow ID: {workflow_id}")
        
        # Check workflow status
        status = workflows.get_workflow_status(workflow_id)
        if status:
            print(f"   Status: {status.status.value}")
            print(f"   Duration: {status.duration_seconds:.2f}s" if status.duration_seconds else "In progress")
        
        # Get performance dashboard data
        print("\n2. Performance Dashboard Data:")
        dashboard_data = workflows.get_performance_dashboard_data(agent_id)
        print(f"   Active Patterns: {dashboard_data['active_patterns_count']}")
        print(f"   Recent Workflows: {len(dashboard_data['recent_workflows'])}")
        
        # Get comprehensive performance analysis
        print("\n3. Performance Analysis:")
        performance = workflows.get_comprehensive_performance_analysis(agent_id, period_days=30)
        if "error" not in performance:
            basic = performance["basic_metrics"]
            print(f"   Total Trades: {basic['total_trades']}")
            print(f"   Win Rate: {basic['win_rate']:.1%}")
            print(f"   Total P&L: {basic['total_pnl']:.2f}")
            print(f"   Profit Factor: {basic['profit_factor']:.2f}")
        else:
            print(f"   Error: {performance['error']}")
        
        print("\nDemo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
    finally:
        client.close()