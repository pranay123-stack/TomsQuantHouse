"""
Message Schemas and Communication Protocols for Agent Coordination
Defines standardized message formats for different types of agent communications
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from datetime import datetime
import uuid


class MessageType(Enum):
    # Trading signals
    TRADE_SIGNAL = "trade_signal"
    EXECUTION_RESULT = "execution_result"
    ORDER_UPDATE = "order_update"
    
    # Predictions and analysis
    PREDICTION = "prediction"
    ANALYSIS_RESULT = "analysis_result"
    MODEL_UPDATE = "model_update"
    
    # Alerts and notifications
    ALERT = "alert"
    NOTIFICATION = "notification"
    SYSTEM_STATUS = "system_status"
    
    # Agent coordination
    AGENT_REGISTER = "agent_register"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_DISCOVER = "agent_discover"
    COORDINATION_REQUEST = "coordination_request"
    
    # Message flow control
    ACKNOWLEDGMENT = "acknowledgment"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class MessageStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    REPLAYED = "replayed"


@dataclass
class TradeSignal:
    """Trade signal message schema"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    strategy: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Prediction:
    """Prediction message schema"""
    symbol: str
    predicted_direction: str  # UP, DOWN, SIDEWAYS
    predicted_price: float
    timeframe: str  # 1h, 4h, 1d, etc.
    confidence: float
    model_version: str
    features_used: List[str] = field(default_factory=list)
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert message schema"""
    alert_type: str  # PRICE_THRESHOLD, VOLATILITY, ERROR, etc.
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    title: str
    message: str
    symbol: Optional[str] = None
    threshold: Optional[float] = None
    current_value: Optional[float] = None
    auto_resolve: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Analysis result message schema"""
    analysis_type: str  # TECHNICAL, FUNDAMENTAL, SENTIMENT, etc.
    symbol: str
    results: Dict[str, Any]
    timestamp: datetime
    confidence: float
    recommendation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetadata:
    """Agent metadata for registration and discovery"""
    agent_id: str
    agent_type: str
    name: str
    version: str
    capabilities: List[str] = field(default_factory=list)
    supported_symbols: List[str] = field(default_factory=list)
    max_capacity: int = 100
    current_load: float = 0.0
    last_heartbeat: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemStatus:
    """System status message schema"""
    component: str
    status: str  # HEALTHY, DEGRADED, CRITICAL
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    active_connections: Optional[int] = None
    messages_per_second: Optional[float] = None
    error_rate: Optional[float] = None
    uptime: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtocolMessage:
    """Standardized message protocol"""
    # Message identification
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    # Communication details
    sender_id: str
    recipient_id: Optional[str] = None
    channel: str = "general"
    message_type: MessageType = MessageType.NOTIFICATION
    
    # Message content
    title: Optional[str] = None
    content: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Trade signal data
    trade_signal: Optional[TradeSignal] = None
    prediction: Optional[Prediction] = None
    alert: Optional[Alert] = None
    analysis_result: Optional[AnalysisResult] = None
    agent_metadata: Optional[AgentMetadata] = None
    system_status: Optional[SystemStatus] = None
    
    # Message control
    priority: int = 2  # 1-4 (LOW to CRITICAL)
    requires_acknowledgment: bool = False
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None  # seconds
    
    # Status tracking
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    
    # Error handling
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Security
    encrypted: bool = False
    signature: Optional[str] = None
    encryption_key_id: Optional[str] = None
    
    # Message flow
    ttl: Optional[int] = None  # Time to live in seconds
    replay_count: int = 0
    
    def __post_init__(self):
        """Validate message after creation"""
        if self.message_type == MessageType.TRADE_SIGNAL and not self.trade_signal:
            raise ValueError("Trade signal message requires trade_signal payload")
        elif self.message_type == MessageType.PREDICTION and not self.prediction:
            raise ValueError("Prediction message requires prediction payload")
        elif self.message_type == MessageType.ALERT and not self.alert:
            raise ValueError("Alert message requires alert payload")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (MessageType, MessageStatus)):
                result[key] = value.value
            elif hasattr(value, '__dict__'):
                result[key] = value.__dict__ if value else None
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProtocolMessage':
        """Create message from dictionary"""
        # Convert datetime strings
        for field_name in ['created_at', 'sent_at', 'delivered_at', 'acknowledged_at']:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])
        
        # Convert enums
        if 'message_type' in data:
            data['message_type'] = MessageType(data['message_type'])
        if 'status' in data:
            data['status'] = MessageStatus(data['status'])
        
        # Convert complex objects
        if data.get('trade_signal') and isinstance(data['trade_signal'], dict):
            data['trade_signal'] = TradeSignal(**data['trade_signal'])
        if data.get('prediction') and isinstance(data['prediction'], dict):
            data['prediction'] = Prediction(**data['prediction'])
        if data.get('alert') and isinstance(data['alert'], dict):
            data['alert'] = Alert(**data['alert'])
        if data.get('analysis_result') and isinstance(data['analysis_result'], dict):
            data['analysis_result'] = AnalysisResult(**data['analysis_result'])
        if data.get('agent_metadata') and isinstance(data['agent_metadata'], dict):
            data['agent_metadata'] = AgentMetadata(**data['agent_metadata'])
        if data.get('system_status') and isinstance(data['system_status'], dict):
            data['system_status'] = SystemStatus(**data['system_status'])
        
        return cls(**data)
    
    def create_response(self, recipient_id: str, content: str = None, 
                       status: MessageStatus = MessageStatus.DELIVERED) -> 'ProtocolMessage':
        """Create a response to this message"""
        return ProtocolMessage(
            correlation_id=self.message_id,
            reply_to=self.sender_id,
            sender_id=recipient_id,
            recipient_id=self.sender_id,
            channel=self.channel,
            message_type=MessageType.ACKNOWLEDGMENT if status == MessageStatus.ACKNOWLEDGED else MessageType.NOTIFICATION,
            content=content,
            payload=self.payload.copy() if self.payload else {},
            status=status
        )
    
    def mark_sent(self):
        """Mark message as sent"""
        self.status = MessageStatus.SENT
        self.sent_at = datetime.utcnow()
    
    def mark_delivered(self):
        """Mark message as delivered"""
        self.status = MessageStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
    
    def mark_acknowledged(self):
        """Mark message as acknowledged"""
        self.status = MessageStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
    
    def mark_failed(self, error_code: str, error_message: str, stack_trace: str = None):
        """Mark message as failed"""
        self.status = MessageStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message
        self.stack_trace = stack_trace
    
    def is_expired(self) -> bool:
        """Check if message is expired"""
        if not self.ttl:
            return False
        return (datetime.utcnow() - self.created_at).seconds > self.ttl
    
    def needs_retry(self) -> bool:
        """Check if message should be retried"""
        return (self.status == MessageStatus.FAILED and 
                self.retry_count < self.max_retries)


# Message factory for creating common message types
class MessageFactory:
    """Factory for creating standardized messages"""
    
    @staticmethod
    def create_trade_signal(sender_id: str, trade_signal: TradeSignal, 
                          priority: int = 3, channel: str = "trading") -> ProtocolMessage:
        """Create a trade signal message"""
        return ProtocolMessage(
            sender_id=sender_id,
            channel=channel,
            message_type=MessageType.TRADE_SIGNAL,
            title=f"Trade Signal: {trade_signal.symbol}",
            trade_signal=trade_signal,
            priority=priority,
            requires_acknowledgment=True
        )
    
    @staticmethod
    def create_prediction(sender_id: str, prediction: Prediction, 
                        priority: int = 2, channel: str = "predictions") -> ProtocolMessage:
        """Create a prediction message"""
        return ProtocolMessage(
            sender_id=sender_id,
            channel=channel,
            message_type=MessageType.PREDICTION,
            title=f"Prediction: {prediction.symbol}",
            prediction=prediction,
            priority=priority
        )
    
    @staticmethod
    def create_alert(sender_id: str, alert: Alert, priority: int = 4, 
                    channel: str = "alerts") -> ProtocolMessage:
        """Create an alert message"""
        return ProtocolMessage(
            sender_id=sender_id,
            channel=channel,
            message_type=MessageType.ALERT,
            title=f"Alert: {alert.title}",
            alert=alert,
            priority=priority,
            requires_acknowledgment=True
        )
    
    @staticmethod
    def create_agent_registration(agent_metadata: AgentMetadata) -> ProtocolMessage:
        """Create an agent registration message"""
        return ProtocolMessage(
            sender_id=agent_metadata.agent_id,
            channel="agent_registration",
            message_type=MessageType.AGENT_REGISTER,
            title=f"Agent Registration: {agent_metadata.name}",
            agent_metadata=agent_metadata,
            priority=3,
            requires_acknowledgment=True
        )
    
    @staticmethod
    def create_heartbeat(agent_id: str, status: Dict[str, Any] = None) -> ProtocolMessage:
        """Create a heartbeat message"""
        return ProtocolMessage(
            sender_id=agent_id,
            channel="heartbeats",
            message_type=MessageType.HEARTBEAT,
            title=f"Heartbeat from {agent_id}",
            payload=status or {},
            priority=1
        )
    
    @staticmethod
    def create_error(sender_id: str, correlation_id: str, error_code: str, 
                    error_message: str, channel: str = "errors") -> ProtocolMessage:
        """Create an error message"""
        return ProtocolMessage(
            sender_id=sender_id,
            channel=channel,
            message_type=MessageType.ERROR,
            title=f"Error: {error_code}",
            content=error_message,
            correlation_id=correlation_id,
            priority=4,
            requires_acknowledgment=False
        )