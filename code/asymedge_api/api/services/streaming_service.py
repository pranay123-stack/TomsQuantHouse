"""
ASYMEdge Dashboard API - Real-time Streaming Service

Real-time streaming service providing:
- WebSocket connections for live data updates
- Subscription management for different data types
- Real-time agent activity updates
- Live trading metrics streaming
- Workflow status updates
- System monitoring and alerts
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import weakref
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketDisconnect
from api.schemas import WebSocketMessage, AgentUpdateMessage, MetricUpdateMessage, WorkflowUpdateMessage

logger = logging.getLogger(__name__)

class SubscriptionType(str, Enum):
    """Types of real-time subscriptions"""
    AGENT_ACTIVITY = "agent_activity"
    TRADING_METRICS = "trading_metrics"
    WORKFLOW_STATUS = "workflow_status"
    MARKET_DATA = "market_data"
    SYSTEM_ALERTS = "system_alerts"
    PORTFOLIO_UPDATES = "portfolio_updates"
    USER_ACTIVITY = "user_activity"

class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class StreamSubscription:
    """Real-time subscription definition"""
    subscription_id: str
    user_id: int
    subscription_type: SubscriptionType
    filters: Dict[str, Any]
    websocket: WebSocket
    is_active: bool = True
    last_heartbeat: Optional[datetime] = None
    message_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class StreamMessage:
    """Stream message structure"""
    message_id: str
    subscription_type: SubscriptionType
    priority: MessagePriority
    data: Dict[str, Any]
    timestamp: datetime = None
    recipient_filter: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class ConnectionManager:
    """Manage WebSocket connections and subscriptions"""
    
    def __init__(self):
        # Active connections by user
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        # Active subscriptions
        self.subscriptions: Dict[str, StreamSubscription] = {}
        # Connection to subscription mapping
        self.connection_subscriptions: Dict[WebSocket, Set[str]] = {}
        
        # Message queues for different priority levels
        self.high_priority_queue: asyncio.Queue = asyncio.Queue()
        self.normal_priority_queue: asyncio.Queue = asyncio.Queue()
        self.low_priority_queue: asyncio.Queue = asyncio.Queue()
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
    async def connect(self, websocket: WebSocket, user_id: int) -> str:
        """Accept WebSocket connection and return subscription ID"""
        await websocket.accept()
        
        subscription_id = f"sub-{uuid.uuid4().hex[:8]}"
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        # Track connection subscriptions
        self.connection_subscriptions[websocket] = set()
        
        logger.info(f"WebSocket connected for user {user_id}, subscription ID: {subscription_id}")
        return subscription_id
    
    async def disconnect(self, websocket: WebSocket, user_id: int):
        """Disconnect WebSocket and cleanup subscriptions"""
        try:
            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove all subscriptions for this connection
            if websocket in self.connection_subscriptions:
                subscription_ids = self.connection_subscriptions[websocket].copy()
                for sub_id in subscription_ids:
                    await self.unsubscribe(websocket, sub_id)
                del self.connection_subscriptions[websocket]
            
            logger.info(f"WebSocket disconnected for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def subscribe(self, websocket: WebSocket, user_id: int, 
                       subscription_type: SubscriptionType, 
                       filters: Dict[str, Any] = None) -> str:
        """Create a new subscription"""
        subscription_id = f"sub-{uuid.uuid4().hex[:8]}"
        
        subscription = StreamSubscription(
            subscription_id=subscription_id,
            user_id=user_id,
            subscription_type=subscription_type,
            filters=filters or {},
            websocket=websocket
        )
        
        self.subscriptions[subscription_id] = subscription
        self.connection_subscriptions[websocket].add(subscription_id)
        
        logger.info(f"Created subscription {subscription_id} for user {user_id}: {subscription_type}")
        return subscription_id
    
    async def unsubscribe(self, websocket: WebSocket, subscription_id: str):
        """Remove a subscription"""
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions[subscription_id]
            subscription.is_active = False
            
            # Remove from connection mapping
            if websocket in self.connection_subscriptions:
                self.connection_subscriptions[websocket].discard(subscription_id)
            
            # Remove subscription
            del self.subscriptions[subscription_id]
            
            logger.info(f"Removed subscription {subscription_id}")
    
    async def send_message(self, subscription_id: str, message: StreamMessage):
        """Send message to specific subscription"""
        if subscription_id not in self.subscriptions:
            return
        
        subscription = self.subscriptions[subscription_id]
        if not subscription.is_active or not subscription.websocket:
            return
        
        try:
            # Create WebSocket message
            ws_message = {
                "type": "data_update",
                "subscription_type": subscription.subscription_type.value,
                "data": message.data,
                "timestamp": message.timestamp.isoformat(),
                "priority": message.priority.value
            }
            
            await subscription.websocket.send_text(json.dumps(ws_message))
            subscription.message_count += 1
            
        except WebSocketDisconnect:
            # Connection lost, mark as inactive
            subscription.is_active = False
            logger.warning(f"WebSocket disconnected while sending message to {subscription_id}")
        except Exception as e:
            logger.error(f"Failed to send message to subscription {subscription_id}: {e}")
    
    async def broadcast_message(self, subscription_type: SubscriptionType, 
                              message: StreamMessage, 
                              filter_func: Optional[Callable] = None):
        """Broadcast message to all matching subscriptions"""
        tasks = []
        
        for subscription_id, subscription in self.subscriptions.items():
            if (subscription.is_active and 
                subscription.subscription_type == subscription_type):
                
                # Apply filters
                if filter_func and not filter_func(subscription, message):
                    continue
                
                tasks.append(self.send_message(subscription_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """Send message to all connections for a user"""
        if user_id not in self.user_connections:
            return
        
        tasks = []
        for websocket in self.user_connections[user_id]:
            try:
                await websocket.send_text(json.dumps(message))
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Yield control
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_active_subscriptions(self, user_id: int) -> List[StreamSubscription]:
        """Get all active subscriptions for a user"""
        return [
            sub for sub in self.subscriptions.values()
            if sub.user_id == user_id and sub.is_active
        ]
    
    async def cleanup_inactive_connections(self):
        """Clean up inactive connections and subscriptions"""
        current_time = datetime.now()
        inactive_threshold = timedelta(minutes=5)
        
        inactive_subscriptions = []
        
        for sub_id, subscription in self.subscriptions.items():
            # Check for heartbeat timeout
            if (subscription.last_heartbeat and 
                current_time - subscription.last_heartbeat > inactive_threshold):
                inactive_subscriptions.append(sub_id)
        
        # Remove inactive subscriptions
        for sub_id in inactive_subscriptions:
            subscription = self.subscriptions[sub_id]
            subscription.is_active = False
            
            # Remove from connection mapping
            if subscription.websocket in self.connection_subscriptions:
                self.connection_subscriptions[subscription.websocket].discard(sub_id)
            
            del self.subscriptions[sub_id]
            logger.info(f"Cleaned up inactive subscription {sub_id}")

class RealTimeStreamingService:
    """Main streaming service for real-time data updates"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.data_generators = {
            SubscriptionType.AGENT_ACTIVITY: self._generate_agent_updates,
            SubscriptionType.TRADING_METRICS: self._generate_metric_updates,
            SubscriptionType.WORKFLOW_STATUS: self._generate_workflow_updates,
            SubscriptionType.MARKET_DATA: self._generate_market_updates,
            SubscriptionType.SYSTEM_ALERTS: self._generate_system_alerts,
            SubscriptionType.PORTFOLIO_UPDATES: self._generate_portfolio_updates,
            SubscriptionType.USER_ACTIVITY: self._generate_user_activity_updates
        }
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for data generation"""
        # Data generation tasks
        for subscription_type in SubscriptionType:
            task = asyncio.create_task(
                self._data_generation_loop(subscription_type)
            )
            self.connection_manager.background_tasks.append(task)
        
        # Cleanup task
        cleanup_task = asyncio.create_task(
            self._cleanup_loop()
        )
        self.connection_manager.background_tasks.append(cleanup_task)
    
    async def handle_websocket_connection(self, websocket: WebSocket, user_id: int, 
                                        subscription_configs: List[Dict[str, Any]]):
        """Handle WebSocket connection and subscriptions"""
        try:
            # Connect
            connection_id = await self.connection_manager.connect(websocket, user_id)
            
            # Create subscriptions
            subscription_ids = []
            for config in subscription_configs:
                sub_type = SubscriptionType(config["type"])
                filters = config.get("filters", {})
                
                sub_id = await self.connection_manager.subscribe(
                    websocket, user_id, sub_type, filters
                )
                subscription_ids.append(sub_id)
            
            # Send connection confirmation
            confirmation_message = {
                "type": "connection_established",
                "connection_id": connection_id,
                "subscription_ids": subscription_ids,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(confirmation_message))
            
            # Handle incoming messages (heartbeats, commands, etc.)
            await self._handle_websocket_messages(websocket, user_id)
            
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            await self.connection_manager.disconnect(websocket, user_id)
    
    async def _handle_websocket_messages(self, websocket: WebSocket, user_id: int):
        """Handle incoming WebSocket messages"""
        try:
            while True:
                # Receive message
                message_text = await websocket.receive_text()
                message_data = json.loads(message_text)
                
                # Handle different message types
                message_type = message_data.get("type")
                
                if message_type == "ping":
                    # Handle heartbeat
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
                elif message_type == "update_subscription":
                    # Update existing subscription
                    subscription_id = message_data.get("subscription_id")
                    filters = message_data.get("filters", {})
                    
                    if subscription_id in self.connection_manager.subscriptions:
                        subscription = self.connection_manager.subscriptions[subscription_id]
                        subscription.filters.update(filters)
                        
                elif message_type == "unsubscribe":
                    # Unsubscribe from a subscription
                    subscription_id = message_data.get("subscription_id")
                    await self.connection_manager.unsubscribe(websocket, subscription_id)
                    
                elif message_type == "command":
                    # Handle custom commands
                    command = message_data.get("command")
                    await self._handle_command(user_id, command, message_data)
                    
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.error(f"Error handling WebSocket messages: {e}")
    
    async def _handle_command(self, user_id: int, command: str, message_data: Dict[str, Any]):
        """Handle custom commands from WebSocket"""
        try:
            if command == "get_status":
                # Get current status
                subscriptions = await self.connection_manager.get_active_subscriptions(user_id)
                status = {
                    "type": "status_response",
                    "subscriptions": [
                        {
                            "id": sub.subscription_id,
                            "type": sub.subscription_type.value,
                            "filters": sub.filters,
                            "message_count": sub.message_count,
                            "created_at": sub.created_at.isoformat()
                        }
                        for sub in subscriptions
                    ]
                }
                
                await self.connection_manager.send_to_user(user_id, status)
                
        except Exception as e:
            logger.error(f"Error handling command {command}: {e}")
    
    async def publish_agent_update(self, agent_id: int, status: str, 
                                 activity: str = None, performance: Dict[str, float] = None):
        """Publish agent activity update"""
        update_message = StreamMessage(
            message_id=f"agent-{uuid.uuid4().hex[:8]}",
            subscription_type=SubscriptionType.AGENT_ACTIVITY,
            priority=MessagePriority.NORMAL,
            data={
                "agent_id": agent_id,
                "status": status,
                "activity": activity,
                "performance": performance or {}
            }
        )
        
        await self.connection_manager.broadcast_message(
            SubscriptionType.AGENT_ACTIVITY,
            update_message,
            filter_func=lambda sub, msg: sub.filters.get("agent_id") == agent_id or "all" in sub.filters
        )
    
    async def publish_metric_update(self, metric_type: str, value: float, 
                                  symbol: str = None, metadata: Dict[str, Any] = None):
        """Publish trading metric update"""
        update_message = StreamMessage(
            message_id=f"metric-{uuid.uuid4().hex[:8]}",
            subscription_type=SubscriptionType.TRADING_METRICS,
            priority=MessagePriority.NORMAL,
            data={
                "metric_type": metric_type,
                "value": value,
                "symbol": symbol,
                "metadata": metadata or {}
            }
        )
        
        await self.connection_manager.broadcast_message(
            SubscriptionType.TRADING_METRICS,
            update_message,
            filter_func=lambda sub, msg: (
                sub.filters.get("metric_type") == metric_type or 
                "all" in sub.filters
            )
        )
    
    async def publish_workflow_update(self, workflow_id: int, status: str, 
                                    current_step: str = None, progress: float = None,
                                    output: Dict[str, Any] = None, error: str = None):
        """Publish workflow status update"""
        update_message = StreamMessage(
            message_id=f"workflow-{uuid.uuid4().hex[:8]}",
            subscription_type=SubscriptionType.WORKFLOW_STATUS,
            priority=MessagePriority.HIGH,
            data={
                "workflow_id": workflow_id,
                "status": status,
                "current_step": current_step,
                "progress": progress or 0.0,
                "output": output,
                "error": error
            }
        )
        
        await self.connection_manager.broadcast_message(
            SubscriptionType.WORKFLOW_STATUS,
            update_message,
            filter_func=lambda sub, msg: sub.filters.get("workflow_id") == workflow_id or "all" in sub.filters
        )
    
    async def publish_system_alert(self, alert_type: str, message: str, 
                                 severity: str = "normal", metadata: Dict[str, Any] = None):
        """Publish system alert"""
        priority = MessagePriority.HIGH if severity == "critical" else MessagePriority.NORMAL
        
        alert_message = StreamMessage(
            message_id=f"alert-{uuid.uuid4().hex[:8]}",
            subscription_type=SubscriptionType.SYSTEM_ALERTS,
            priority=priority,
            data={
                "alert_type": alert_type,
                "message": message,
                "severity": severity,
                "metadata": metadata or {}
            }
        )
        
        await self.connection_manager.broadcast_message(
            SubscriptionType.SYSTEM_ALERTS,
            alert_message
        )
    
    # Background data generation methods
    async def _data_generation_loop(self, subscription_type: SubscriptionType):
        """Background loop for generating data updates"""
        generator = self.data_generators.get(subscription_type)
        if not generator:
            return
        
        while True:
            try:
                await generator()
                await asyncio.sleep(1)  # Generate updates every second
            except Exception as e:
                logger.error(f"Error in data generation loop for {subscription_type}: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _cleanup_loop(self):
        """Background loop for cleanup tasks"""
        while True:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                await self.connection_manager.cleanup_inactive_connections()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def _generate_agent_updates(self):
        """Generate mock agent activity updates"""
        # Simulate random agent activity
        agent_ids = [1, 2, 3, 4, 5]
        agent_id = agent_ids[hash(str(datetime.now().second)) % len(agent_ids)]
        
        activities = ["processing_query", "analyzing_data", "monitoring_portfolio", "generating_report"]
        activity = activities[hash(str(datetime.now().microsecond)) % len(activities)]
        
        await self.publish_agent_update(agent_id, "running", activity)
    
    async def _generate_metric_updates(self):
        """Generate mock metric updates"""
        metrics = [
            ("portfolio_value", 100000.0 + hash(str(datetime.now())) % 10000),
            ("portfolio_pnl", hash(str(datetime.now().microsecond)) % 1000 - 500),
            ("daily_pnl", hash(str(datetime.now().second)) % 100 - 50),
            ("risk_score", 0.1 + (hash(str(datetime.now().microsecond)) % 100) / 1000)
        ]
        
        metric_type, value = metrics[hash(str(datetime.now().microsecond)) % len(metrics)]
        await self.publish_metric_update(metric_type, value)
    
    async def _generate_workflow_updates(self):
        """Generate mock workflow updates"""
        # Only generate updates occasionally
        if hash(str(datetime.now().second)) % 10 != 0:
            return
        
        workflow_ids = [1, 2, 3]
        workflow_id = workflow_ids[hash(str(datetime.now().second)) % len(workflow_ids)]
        
        statuses = ["running", "completed", "failed"]
        status = statuses[hash(str(datetime.now().microsecond)) % len(statuses)]
        
        await self.publish_workflow_update(
            workflow_id, 
            status, 
            current_step="processing_data",
            progress=0.75 if status == "running" else 1.0
        )
    
    async def _generate_market_updates(self):
        """Generate mock market data updates"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        symbol = symbols[hash(str(datetime.now().second)) % len(symbols)]
        
        # Simulate price movement
        base_price = {"AAPL": 150, "GOOGL": 2800, "MSFT": 350, "TSLA": 200}[symbol]
        price_change = (hash(str(datetime.now().microsecond)) % 200 - 100) / 100
        price = base_price + price_change
        
        await self.connection_manager.broadcast_message(
            SubscriptionType.MARKET_DATA,
            StreamMessage(
                message_id=f"market-{uuid.uuid4().hex[:8]}",
                subscription_type=SubscriptionType.MARKET_DATA,
                priority=MessagePriority.LOW,
                data={
                    "symbol": symbol,
                    "price": price,
                    "volume": hash(str(datetime.now().microsecond)) % 1000000,
                    "timestamp": datetime.now().isoformat()
                }
            )
        )
    
    async def _generate_system_alerts(self):
        """Generate mock system alerts"""
        # Very rarely generate alerts
        if hash(str(datetime.now().minute)) % 30 != 0:
            return
        
        alert_types = ["high_cpu", "low_memory", "network_timeout", "agent_error"]
        alert_type = alert_types[hash(str(datetime.now().second)) % len(alert_types)]
        
        await self.publish_system_alert(alert_type, f"{alert_type} detected", "high")
    
    async def _generate_portfolio_updates(self):
        """Generate mock portfolio updates"""
        await self.connection_manager.broadcast_message(
            SubscriptionType.PORTFOLIO_UPDATES,
            StreamMessage(
                message_id=f"portfolio-{uuid.uuid4().hex[:8]}",
                subscription_type=SubscriptionType.PORTFOLIO_UPDATES,
                priority=MessagePriority.NORMAL,
                data={
                    "total_value": 100000.0 + hash(str(datetime.now())) % 50000,
                    "cash_position": 10000.0 + hash(str(datetime.now().microsecond)) % 5000,
                    "positions": [
                        {"symbol": "AAPL", "value": 25000, "quantity": 167},
                        {"symbol": "GOOGL", "value": 30000, "quantity": 11},
                        {"symbol": "MSFT", "value": 20000, "quantity": 57}
                    ],
                    "timestamp": datetime.now().isoformat()
                }
            )
        )
    
    async def _generate_user_activity_updates(self):
        """Generate mock user activity updates"""
        # Only generate occasionally
        if hash(str(datetime.now().minute)) % 5 != 0:
            return
        
        await self.connection_manager.broadcast_message(
            SubscriptionType.USER_ACTIVITY,
            StreamMessage(
                message_id=f"user-{uuid.uuid4().hex[:8]}",
                subscription_type=SubscriptionType.USER_ACTIVITY,
                priority=MessagePriority.LOW,
                data={
                    "activity": "dashboard_view",
                    "timestamp": datetime.now().isoformat(),
                    "session_duration": hash(str(datetime.now().microsecond)) % 3600
                }
            )
        )

# Global streaming service instance
streaming_service = RealTimeStreamingService()