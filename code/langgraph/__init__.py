"""
LangGraph Workflow System
Comprehensive LangGraph-based trading workflow system with Redis checkpointing
"""

__version__ = "1.0.0"
__author__ = "Trading Framework Team"

# Core imports
from .workflows.trading_workflow import TradingWorkflow
from .workflows.state_graph import TradingStateGraph  
from .workflows.state import WorkflowState, WorkflowStatus
from .checkpoints.redis_checkpointer import RedisCheckpointer
from .visualization.monitoring import WorkflowVisualization, WorkflowMonitoring
from .utils.workflow_utils import WorkflowUtils

# API imports
try:
    from .api.workflow_api import create_workflow_api, run_api_server
except ImportError:
    # FastAPI not installed, API will be unavailable
    create_workflow_api = None
    run_api_server = None

__all__ = [
    "TradingWorkflow",
    "TradingStateGraph",
    "WorkflowState", 
    "WorkflowStatus",
    "RedisCheckpointer",
    "WorkflowVisualization",
    "WorkflowMonitoring",
    "WorkflowUtils",
    "create_workflow_api",
    "run_api_server"
]