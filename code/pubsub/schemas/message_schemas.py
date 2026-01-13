"""
Message schemas and data models for the agent communication system.
Defines standardized message formats, validation, and serialization.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import uuid
import hashlib


class MessageType(Enum):
    """Types of messages in the system"""
    TRADE_SIGNAL = "trade_signal"
    PREDICTION = "prediction"
    ALERT = "alert"
    AGENT_COORDINATION = "agent_coordination"
    MARKET_UPDATE = "market_update"
    STRATEGY_UPDATE = "strategy_update"
    HEARTBEAT = "heartbeat"
    DISCOVERY = "discovery"
    COMMAND = "command"
    STATUS = "status"


class Priority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class DeliveryGuarantee(Enum):
    """Message delivery guarantees"""
    BEST_EFFORT = "best_effort"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"
    ORDERED = "ordered"


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    endpoint: str
    version: str = "1.0"
    registered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageMetadata:
    """Message metadata for routing and tracking"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None  # Time to live in seconds
    priority: Priority = Priority.NORMAL
    delivery_guarantee: DeliveryGuarantee = DeliveryGuarantee.BEST_EFFORT
    retries: int = 0
    max_retries: int = 3
    encrypted: bool = False
    signature: Optional[str] = None
    routing_key: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class BaseMessage:
    """Base message class with common fields"""
    message_type: MessageType
    sender_id: str
    recipient_id: Optional[str] = None
    channel: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        data = {
            'message_type': self.message_type.value,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'channel': self.channel,
            'payload': self.payload,
            'metadata': {
                'message_id': self.metadata.message_id,
                'correlation_id': self.metadata.correlation_id,
                'reply_to': self.metadata.reply_to,
                'timestamp': self.metadata.timestamp.isoformat(),
                'ttl': self.metadata.ttl,
                'priority': self.metadata.priority.value,
                'delivery_guarantee': self.metadata.delivery_guarantee.value,
                'retries': self.metadata.retries,
                'max_retries': self.metadata.max_retries,
                'encrypted': self.metadata.encrypted,
                'signature': self.metadata.signature,
                'routing_key': self.metadata.routing_key,
                'tags': self.metadata.tags
            }
        }
        return json.dumps(data, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseMessage':
        """Create message from JSON string"""
        data = json.loads(json_str)
        
        metadata = MessageMetadata(
            message_id=data['metadata']['message_id'],
            correlation_id=data['metadata'].get('correlation_id'),
            reply_to=data['metadata'].get('reply_to'),
            timestamp=datetime.fromisoformat(data['metadata']['timestamp']),
            ttl=data['metadata'].get('ttl'),
            priority=Priority(data['metadata']['priority']),
            delivery_guarantee=DeliveryGuarantee(data['metadata']['delivery_guarantee']),
            retries=data['metadata'].get('retries', 0),
            max_retries=data['metadata'].get('max_retries', 3),
            encrypted=data['metadata'].get('encrypted', False),
            signature=data['metadata'].get('signature'),
            routing_key=data['metadata'].get('routing_key'),
            tags=data['metadata'].get('tags', [])
        )
        
        return cls(
            message_type=MessageType(data['message_type']),
            sender_id=data['sender_id'],
            recipient_id=data.get('recipient_id'),
            channel=data.get('channel'),
            payload=data.get('payload', {}),
            metadata=metadata
        )
    
    def get_message_hash(self) -> str:
        """Generate hash for message integrity"""
        content = f"{self.sender_id}:{self.payload}:{self.metadata.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class TradeSignalMessage(BaseMessage):
    """Trade signal message"""
    def __post_init__(self):
        self.message_type = MessageType.TRADE_SIGNAL
        
        # Validate required fields
        required_fields = ['symbol', 'signal', 'price', 'timestamp']
        for field in required_fields:
            if field not in self.payload:
                raise ValueError(f"Missing required field: {field}")
        
        # Set default metadata
        self.metadata.routing_key = f"signals.{self.payload['symbol']}.{self.payload['signal'].lower()}"
        self.metadata.tags = ['trading', 'signal', self.payload['symbol']]


@dataclass
class PredictionMessage(BaseMessage):
    """ML prediction message"""
    def __post_init__(self):
        self.message_type = MessageType.PREDICTION
        
        # Set default metadata
        model_name = self.payload.get('model', 'unknown')
        confidence = self.payload.get('confidence', 0.0)
        
        self.metadata.routing_key = f"predictions.{model_name}.{confidence:.1f}"
        self.metadata.tags = ['prediction', 'ml', model_name]


@dataclass
class AlertMessage(BaseMessage):
    """Alert message"""
    def __post_init__(self):
        self.message_type = MessageType.ALERT
        
        # Validate required fields
        if 'alert_type' not in self.payload:
            raise ValueError("Missing required field: alert_type")
        if 'message' not in self.payload:
            raise ValueError("Missing required field: message")
        
        # Set default metadata based on alert type
        alert_type = self.payload['alert_type'].lower()
        self.metadata.priority = {
            'info': Priority.LOW,
            'warning': Priority.NORMAL,
            'error': Priority.HIGH,
            'critical': Priority.CRITICAL,
            'emergency': Priority.EMERGENCY
        }.get(alert_type, Priority.NORMAL)
        
        self.metadata.routing_key = f"alerts.{alert_type}"
        self.metadata.tags = ['alert', alert_type]


@dataclass
class AgentCoordinationMessage(BaseMessage):
    """Agent coordination message"""
    def __post_init__(self):
        self.message_type = MessageType.AGENT_COORDINATION
        
        # Set default metadata
        action = self.payload.get('action', 'unknown')
        self.metadata.routing_key = f"coordination.{action}"
        self.metadata.tags = ['coordination', 'agent', action]
        self.metadata.delivery_guarantee = DeliveryGuarantee.AT_LEAST_ONCE


@dataclass
class MarketUpdateMessage(BaseMessage):
    """Market data update message"""
    def __post_init__(self):
        self.message_type = MessageType.MARKET_UPDATE
        
        # Set default metadata
        symbol = self.payload.get('symbol', 'unknown')
        self.metadata.routing_key = f"market.{symbol}"
        self.metadata.tags = ['market', 'data', symbol]


@dataclass
class DiscoveryMessage(BaseMessage):
    """Agent discovery message"""
    def __post_init__(self):
        self.message_type = MessageType.DISCOVERY
        
        # Set default metadata
        discovery_type = self.payload.get('type', 'query')
        self.metadata.routing_key = f"discovery.{discovery_type}"
        self.metadata.tags = ['discovery', 'agent']
        self.metadata.delivery_guarantee = DeliveryGuarantee.BEST_EFFORT


@dataclass
class HeartbeatMessage(BaseMessage):
    """Heartbeat message for agent health monitoring"""
    def __post_init__(self):
        self.message_type = MessageType.HEARTBEAT
        
        # Set default metadata
        self.metadata.routing_key = f"heartbeats.{self.sender_id}"
        self.metadata.tags = ['heartbeat', 'health', self.sender_id]
        self.metadata.delivery_guarantee = DeliveryGuarantee.BEST_EFFORT


# Message factory for creating messages
class MessageFactory:
    """Factory for creating messages of different types"""
    
    @staticmethod
    def create_trade_signal(sender_id: str, symbol: str, signal: str, 
                          price: float, **kwargs) -> TradeSignalMessage:
        """Create a trade signal message"""
        payload = {
            'symbol': symbol,
            'signal': signal,
            'price': price,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        return TradeSignalMessage(sender_id=sender_id, payload=payload)
    
    @staticmethod
    def create_prediction(sender_id: str, model: str, prediction: Any, 
                         confidence: float, **kwargs) -> PredictionMessage:
        """Create a prediction message"""
        payload = {
            'model': model,
            'prediction': prediction,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        return PredictionMessage(sender_id=sender_id, payload=payload)
    
    @staticmethod
    def create_alert(sender_id: str, alert_type: str, message: str, 
                    **kwargs) -> AlertMessage:
        """Create an alert message"""
        payload = {
            'alert_type': alert_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        return AlertMessage(sender_id=sender_id, payload=payload)
    
    @staticmethod
    def create_coordination(sender_id: str, action: str, **kwargs) -> AgentCoordinationMessage:
        """Create an agent coordination message"""
        payload = {
            'action': action,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        return AgentCoordinationMessage(sender_id=sender_id, payload=payload)
    
    @staticmethod
    def create_discovery(sender_id: str, discovery_type: str, **kwargs) -> DiscoveryMessage:
        """Create a discovery message"""
        payload = {
            'type': discovery_type,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        return DiscoveryMessage(sender_id=sender_id, payload=payload)
    
    @staticmethod
    def create_heartbeat(sender_id: str, **kwargs) -> HeartbeatMessage:
        """Create a heartbeat message"""
        payload = {
            'timestamp': datetime.now().isoformat(),
            'status': 'alive',
            **kwargs
        }
        return HeartbeatMessage(sender_id=sender_id, payload=payload)


# Validation functions
def validate_message(message: BaseMessage) -> List[str]:
    """Validate message and return list of errors"""
    errors = []
    
    # Check required fields
    if not message.sender_id:
        errors.append("sender_id is required")
    
    if not message.payload:
        errors.append("payload cannot be empty")
    
    # Type-specific validation
    if isinstance(message, TradeSignalMessage):
        required_trade_fields = ['symbol', 'signal', 'price', 'timestamp']
        for field in required_trade_fields:
            if field not in message.payload:
                errors.append(f"TradeSignalMessage missing field: {field}")
    
    elif isinstance(message, AlertMessage):
        if 'alert_type' not in message.payload:
            errors.append("AlertMessage missing field: alert_type")
        if 'message' not in message.payload:
            errors.append("AlertMessage missing field: message")
    
    return errors


# Schema definitions for documentation
MESSAGE_SCHEMAS = {
    'trade_signal': {
        'required': ['symbol', 'signal', 'price', 'timestamp'],
        'optional': ['confidence', 'strategy', 'metadata', 'volume', 'stop_loss', 'take_profit'],
        'examples': {
            'symbol': 'BTCUSDT',
            'signal': 'BUY',
            'price': 45000.0,
            'confidence': 0.85,
            'strategy': 'momentum',
            'volume': 1.5
        }
    },
    'prediction': {
        'required': ['model', 'prediction', 'confidence', 'timestamp'],
        'optional': ['features', 'input_data', 'execution_time', 'model_version'],
        'examples': {
            'model': 'LSTM_v2',
            'prediction': 'price_up',
            'confidence': 0.78,
            'features': ['price_ma', 'volume', 'rsi'],
            'input_data': {'price': 45000, 'volume': 1000000}
        }
    },
    'alert': {
        'required': ['alert_type', 'message', 'timestamp'],
        'optional': ['severity', 'component', 'symbol', 'details'],
        'examples': {
            'alert_type': 'ERROR',
            'message': 'Trading strategy failed',
            'severity': 'high',
            'component': 'strategy_engine',
            'symbol': 'BTCUSDT'
        }
    }
}