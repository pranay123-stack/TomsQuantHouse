"""
Trading Workflow State Definition
Defines the data structure and state management for the LangGraph workflow
"""

from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DecisionOutcome(Enum):
    """Trading decision outcomes"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MarketCondition(Enum):
    """Market condition indicators"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    TRENDING = "trending"

@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    high_24h: float
    low_24h: float
    change_24h: float
    change_percent_24h: float

@dataclass 
class MLFeatures:
    """ML feature structure for predictions"""
    technical_indicators: Dict[str, float]
    sentiment_score: float
    market_regime: str
    momentum_score: float
    volatility_score: float
    features_vector: List[float]

@dataclass
class MLPrediction:
    """ML prediction structure"""
    prediction_id: str
    model_name: str
    decision: DecisionOutcome
    confidence: float
    price_target: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_score: float
    features_used: MLFeatures
    timestamp: datetime

@dataclass
class RiskAssessment:
    """Risk assessment structure"""
    risk_level: RiskLevel
    max_position_size: float
    current_exposure: float
    portfolio_risk: float
    risk_factors: List[str]
    recommended_action: str

@dataclass
class ExecutionOrder:
    """Trading execution order structure"""
    order_id: str
    symbol: str
    action: str
    quantity: float
    order_type: str
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    status: str
    timestamp: datetime

@dataclass
class WorkflowState:
    """Complete workflow state structure"""
    # Execution metadata
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    current_node: str = ""
    
    # Trading context
    market_data: Optional[MarketData] = None
    market_condition: Optional[MarketCondition] = None
    portfolio_context: Dict[str, Any] = field(default_factory=dict)
    
    # ML and predictions
    ml_prediction: Optional[MLPrediction] = None
    prediction_confidence: float = 0.0
    model_version: str = ""
    
    # Risk management
    risk_assessment: Optional[RiskAssessment] = None
    risk_score: float = 0.0
    risk_adjusted_action: Optional[str] = None
    
    # Execution
    execution_order: Optional[ExecutionOrder] = None
    execution_status: str = ""
    execution_result: Dict[str, Any] = field(default_factory=dict)
    
    # Workflow history
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    node_history: List[str] = field(default_factory=list)
    error_log: List[str] = field(default_factory=list)
    
    # Checkpointing
    checkpoint_id: Optional[str] = None
    last_checkpoint_time: Optional[datetime] = None
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

class TradingWorkflowState(TypedDict):
    """Type definition for LangGraph state management"""
    # Core execution data
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    current_node: str
    
    # Market and trading data
    market_data: Optional[MarketData]
    market_condition: Optional[MarketCondition]
    ml_prediction: Optional[MLPrediction]
    prediction_confidence: float
    risk_assessment: Optional[RiskAssessment]
    execution_order: Optional[ExecutionOrder]
    
    # Execution tracking
    execution_history: List[Dict[str, Any]]
    node_history: List[str]
    error_log: List[str]
    
    # Metadata and checkpointing
    metadata: Dict[str, Any]
    checkpoint_id: Optional[str]

class NodeResult:
    """Standard result structure for workflow nodes"""
    def __init__(
        self, 
        node_name: str,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        next_node: Optional[str] = None,
        checkpoint: bool = False
    ):
        self.node_name = node_name
        self.success = success
        self.data = data or {}
        self.error = error
        self.next_node = next_node
        self.checkpoint = checkpoint
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "node_name": self.node_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "next_node": self.next_node,
            "checkpoint": self.checkpoint,
            "timestamp": self.timestamp.isoformat()
        }