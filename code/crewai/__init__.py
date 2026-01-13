"""
CrewAI Trading Agent System
A comprehensive multi-agent system for automated trading

Main interfaces for easy integration and usage.
"""

# Core orchestrator
from orchestration.crew_orchestrator import (
    CrewOrchestrator,
    AsyncCrewOrchestrator,
    create_crew_orchestrator
)

# Approval workflow
from orchestration.approval_workflow import (
    ApprovalWorkflow,
    TradeApprovalWorkflow,
    ApprovalType,
    PriorityLevel,
    ApprovalStatus,
    create_approval_workflow
)

# Memory management
from utils.memory_manager import (
    CrewMemoryManager,
    memory_manager
)

# Caching system
from cache.cache_manager import (
    CacheManager,
    MarketDataCache,
    PredictionCache,
    RiskCache
)

# Specialized agents
from agents.market_research_analyst import (
    MarketResearchAnalyst,
    create_market_research_analyst
)

from agents.ml_prediction_engineer import (
    MLPredictionEngineer,
    create_ml_prediction_engineer
)

from agents.chief_risk_officer import (
    ChiefRiskOfficer,
    create_chief_risk_officer
)

from agents.execution_trader import (
    ExecutionTrader,
    create_execution_trader
)

# Task management
from tasks.task_definitions import (
    MarketResearchTasks,
    MLPredictionTasks,
    RiskManagementTasks,
    ExecutionTasks,
    TaskOrchestrator,
    create_trading_analysis_workflow,
    create_trade_execution_workflow,
    create_portfolio_review_workflow
)

# Configuration
from config.settings import (
    TradingSettings,
    AgentPrompts,
    RedisKeys,
    settings
)

# API interface
try:
    from api.server import app
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "CrewAI Trading Team"

# Quick start functions
def quick_start_analysis(symbol: str, crew_id: str = "quick_start"):
    """
    Quick function to run a complete analysis on a symbol
    
    Args:
        symbol: Stock symbol to analyze
        crew_id: Unique identifier for the trading crew
        
    Returns:
        Analysis results dictionary
    """
    async def _run():
        orchestrator = await create_crew_orchestrator(crew_id, async_mode=True)
        await orchestrator.initialize()
        result = await orchestrator.run_complete_analysis(symbol)
        await orchestrator.shutdown()
        return result
    
    import asyncio
    return asyncio.run(_run())


def quick_execute_trade(trade_request: dict, crew_id: str = "quick_trade"):
    """
    Quick function to execute a trade with approval workflow
    
    Args:
        trade_request: Trade request dictionary with symbol, side, quantity
        crew_id: Unique identifier for the trading crew
        
    Returns:
        Trade execution result
    """
    async def _run():
        orchestrator = await create_crew_orchestrator(crew_id, async_mode=True)
        await orchestrator.initialize()
        result = await orchestrator.execute_trade_workflow(trade_request)
        await orchestrator.shutdown()
        return result
    
    import asyncio
    return asyncio.run(_run())


def quick_portfolio_review(portfolio_data: dict, crew_id: str = "quick_review"):
    """
    Quick function to review a portfolio
    
    Args:
        portfolio_data: Portfolio data with positions, cash, total_value
        crew_id: Unique identifier for the trading crew
        
    Returns:
        Portfolio review results
    """
    async def _run():
        orchestrator = await create_crew_orchestrator(crew_id, async_mode=True)
        await orchestrator.initialize()
        result = await orchestrator.run_portfolio_review(portfolio_data)
        await orchestrator.shutdown()
        return result
    
    import asyncio
    return asyncio.run(_run())


# Main exports
__all__ = [
    # Core classes
    "CrewOrchestrator",
    "AsyncCrewOrchestrator", 
    "create_crew_orchestrator",
    
    # Approval system
    "ApprovalWorkflow",
    "TradeApprovalWorkflow", 
    "ApprovalType",
    "PriorityLevel",
    "ApprovalStatus",
    "create_approval_workflow",
    
    # Memory management
    "CrewMemoryManager",
    "memory_manager",
    
    # Caching
    "CacheManager",
    "MarketDataCache",
    "PredictionCache", 
    "RiskCache",
    
    # Agents
    "MarketResearchAnalyst",
    "create_market_research_analyst",
    "MLPredictionEngineer",
    "create_ml_prediction_engineer",
    "ChiefRiskOfficer", 
    "create_chief_risk_officer",
    "ExecutionTrader",
    "create_execution_trader",
    
    # Tasks
    "MarketResearchTasks",
    "MLPredictionTasks",
    "RiskManagementTasks", 
    "ExecutionTasks",
    "TaskOrchestrator",
    "create_trading_analysis_workflow",
    "create_trade_execution_workflow",
    "create_portfolio_review_workflow",
    
    # Configuration
    "TradingSettings",
    "AgentPrompts", 
    "RedisKeys",
    "settings",
    
    # API
    "app" if API_AVAILABLE else None,
    
    # Quick start functions
    "quick_start_analysis",
    "quick_execute_trade",
    "quick_portfolio_review"
]

# Remove None values from __all__
__all__ = [item for item in __all__ if item is not None]