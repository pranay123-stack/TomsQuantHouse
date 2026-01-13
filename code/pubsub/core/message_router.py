"""
Message Routing System with Priority Handling and Delivery Guarantees
Implements advanced message routing, priority queues, and delivery acknowledgment
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import uuid
import hashlib
import weakref
import threading
import time
import logging

from core.redis_client import RedisPubSubClient, MessagePriority
from protocols.message_schemas import ProtocolMessage, MessageStatus, MessageType


class RoutingStrategy(Enum):
    """Message routing strategies"""
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    LOAD_BALANCED = "load_balanced"
    BROADCAST = "broadcast"
    DIRECT = "direct"
    FANOUT = "fanout"


class DeliveryGuarantee(Enum):
    """Message delivery guarantees"""
    BEST_EFFORT = "best_effort"
    AT_LEAST_ONCE = "at_least_once"
    AT_MOST_ONCE = "at_most_once"
    EXACTLY_ONCE = "exactly_once"


@dataclass
class RoutingRule:
    """Message routing rule configuration"""
    rule_id: str
    pattern: str  # Channel or message type pattern
    destination: str  # Target agent or channel
    priority: MessagePriority = MessagePriority.NORMAL
    strategy: RoutingStrategy = RoutingStrategy.DIRECT
    delivery_guarantee: DeliveryGuarantee = DeliveryGuarantee.BEST_EFFORT
    filters: Dict[str, Any] = field(default_factory=dict)
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    enabled: bool = True


@dataclass
class MessageRoute:
    """Message route information"""
    message_id: str
    source: str
    destinations: List[str]
    priority: MessagePriority
    strategy: RoutingStrategy
    delivery_guarantee: DeliveryGuarantee
    created_at: datetime
    retries: int = 0
    last_attempt: Optional[datetime] = None
    status: str = "pending"  # pending, delivered, failed, expired
    acknowledged_by: Set[str] = field(default_factory=set)


@dataclass
class DeliveryStatus:
    """Message delivery status tracking"""
    message_id: str
    route_id: str
    destination: str
    status: MessageStatus
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageRouter:
    """Advanced message router with priority handling and delivery guarantees"""
    
    def __init__(self, redis_client: RedisPubSubClient):
        self.redis = redis_client
        
        # Routing configuration
        self.routing_rules: Dict[str, RoutingRule] = {}
        self.active_routes: Dict[str, MessageRoute] = {}
        self.delivery_status: Dict[str, DeliveryStatus] = {}
        
        # Priority queues for message processing
        self.priority_queues: Dict[MessagePriority, deque] = {
            priority: deque() for priority in MessagePriority
        }
        
        # Message handlers by priority
        self.priority_handlers: Dict[MessagePriority, List[Callable]] = {
            priority: [] for priority in MessagePriority
        }
        
        # Dead letter queue for failed messages
        self.dead_letter_queue: deque = deque(maxlen=10000)
        
        # Retry mechanisms
        self.retry_queue: Dict[str, asyncio.Task] = {}
        self.retry_intervals = {
            1: 1,   # 1 second
            2: 5,   # 5 seconds
            3: 15,  # 15 seconds
            4: 30   # 30 seconds
        }
        
        # Routing statistics
        self.stats = {
            'messages_routed': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'messages_retried': 0,
            'routing_errors': 0,
            'average_delivery_time': 0.0
        }
        
        # Thread safety
        self.router_lock = threading.RLock()
        
        # Background tasks
        self.processing_tasks: List[asyncio.Task] = []
        self.cleanup_task: Optional[asyncio.Task] = None
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the message router"""
        # Start priority-based processing tasks
        for priority in MessagePriority:
            task = asyncio.create_task(self._process_priority_queue(priority))
            self.processing_tasks.append(task)
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        
        # Load routing rules from Redis
        await self._load_routing_rules()
        
        self.logger.info("Message router started")
    
    async def stop(self):
        """Stop the message router"""
        # Cancel processing tasks
        for task in self.processing_tasks:
            task.cancel()
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Cancel retry tasks
        for task in self.retry_queue.values():
            task.cancel()
        
        self.logger.info("Message router stopped")
    
    async def add_routing_rule(self, rule: RoutingRule) -> bool:
        """Add a routing rule"""
        try:
            self.routing_rules[rule.rule_id] = rule
            
            # Store in Redis for persistence
            rule_key = f"routing_rule:{rule.rule_id}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.setex(
                    rule_key,
                    3600,  # 1 hour expiration
                    json.dumps(rule.__dict__, default=str)
                )
            )
            
            self.logger.info(f"Routing rule {rule.rule_id} added")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add routing rule {rule.rule_id}: {e}")
            return False
    
    async def remove_routing_rule(self, rule_id: str) -> bool:
        """Remove a routing rule"""
        try:
            if rule_id in self.routing_rules:
                del self.routing_rules[rule_id]
                
                # Remove from Redis
                rule_key = f"routing_rule:{rule_id}"
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.delete(rule_key)
                )
                
                self.logger.info(f"Routing rule {rule_id} removed")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to remove routing rule {rule_id}: {e}")
            return False
    
    async def route_message(self, message: ProtocolMessage, 
                          manual_destinations: List[str] = None) -> List[str]:
        """Route a message based on rules and destinations"""
        try:
            with self.router_lock:
                # Determine destinations
                destinations = manual_destinations or await self._find_destinations(message)
                
                if not destinations:
                    self.logger.warning(f"No destinations found for message {message.message_id}")
                    return []
                
                # Create message route
                route = MessageRoute(
                    message_id=message.message_id,
                    source=message.sender_id,
                    destinations=destinations,
                    priority=message.priority,
                    strategy=RoutingStrategy.DIRECT,
                    delivery_guarantee=DeliveryGuarantee.BEST_EFFORT,
                    created_at=datetime.utcnow()
                )
                
                # Apply routing rules
                await self._apply_routing_rules(route, message)
                
                # Add to appropriate priority queue
                self.priority_queues[message.priority].append((message, route))
                
                # Track route
                self.active_routes[message.message_id] = route
                
                # Update statistics
                self.stats['messages_routed'] += 1
                
                self.logger.debug(f"Message {message.message_id} routed to {destinations}")
                return destinations
                
        except Exception as e:
            self.logger.error(f"Failed to route message {message.message_id}: {e}")
            self.stats['routing_errors'] += 1
            return []
    
    async def acknowledge_delivery(self, message_id: str, destination: str, 
                                 success: bool = True, error_message: str = None):
        """Acknowledge message delivery"""
        try:
            delivery_key = f"{message_id}:{destination}"
            
            if delivery_key in self.delivery_status:
                status = self.delivery_status[delivery_key]
                status.status = MessageStatus.ACKNOWLEDGED if success else MessageStatus.FAILED
                status.acknowledged_at = datetime.utcnow()
                
                if not success and error_message:
                    status.error_message = error_message
                
                # Update route status
                route = self.active_routes.get(message_id)
                if route:
                    if success:
                        route.acknowledged_by.add(destination)
                        if len(route.acknowledged_by) == len(route.destinations):
                            route.status = "delivered"
                            self.stats['messages_delivered'] += 1
                    else:
                        route.status = "failed"
                        self.stats['messages_failed'] += 1
                        await self._retry_message(message_id, route)
                
        except Exception as e:
            self.logger.error(f"Failed to acknowledge delivery for {message_id}: {e}")
    
    async def get_delivery_status(self, message_id: str) -> Dict[str, DeliveryStatus]:
        """Get delivery status for a message"""
        status_map = {}
        for key, status in self.delivery_status.items():
            if key.startswith(f"{message_id}:"):
                status_map[key.split(":", 1)[1]] = status
        return status_map
    
    async def retry_failed_messages(self):
        """Retry all failed messages"""
        failed_routes = [
            route for route in self.active_routes.values()
            if route.status == "failed" and route.retries < 5
        ]
        
        for route in failed_routes:
            await self._retry_message(route.message_id, route)
    
    async def _process_priority_queue(self, priority: MessagePriority):
        """Process messages in priority order"""
        while True:
            try:
                if self.priority_queues[priority]:
                    message, route = self.priority_queues[priority].popleft()
                    
                    # Process the message
                    await self._deliver_message(message, route)
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.01)
                else:
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing priority queue {priority}: {e}")
                await asyncio.sleep(1)
    
    async def _deliver_message(self, message: ProtocolMessage, route: MessageRoute):
        """Deliver message to destinations"""
        try:
            # Mark as sent
            message.mark_sent()
            
            # Deliver based on strategy
            if route.strategy == RoutingStrategy.BROADCAST:
                await self._broadcast_message(message, route.destinations)
            elif route.strategy == RoutingStrategy.FANOUT:
                await self._fanout_message(message, route.destinations)
            elif route.strategy == RoutingStrategy.LOAD_BALANCED:
                await self._load_balanced_delivery(message, route.destinations)
            else:  # DIRECT
                await self._direct_delivery(message, route.destinations)
            
            # Track delivery attempts
            for destination in route.destinations:
                delivery_key = f"{message.message_id}:{destination}"
                self.delivery_status[delivery_key] = DeliveryStatus(
                    message_id=message.message_id,
                    route_id=route.message_id,
                    destination=destination,
                    status=MessageStatus.SENT,
                    attempts=1,
                    last_attempt=datetime.utcnow()
                )
            
        except Exception as e:
            self.logger.error(f"Failed to deliver message {message.message_id}: {e}")
    
    async def _direct_delivery(self, message: ProtocolMessage, destinations: List[str]):
        """Deliver message directly to specific destinations"""
        for destination in destinations:
            # Create delivery task
            asyncio.create_task(self._deliver_to_destination(message, destination))
    
    async def _broadcast_message(self, message: ProtocolMessage, destinations: List[str]):
        """Broadcast message to all destinations"""
        # Publish to broadcast channel
        broadcast_channel = f"broadcast:{message.channel}"
        await self.redis.publish(message)
    
    async def _fanout_message(self, message: ProtocolMessage, destinations: List[str]):
        """Fanout message to multiple destinations"""
        tasks = [self._deliver_to_destination(message, dest) for dest in destinations]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _load_balanced_delivery(self, message: ProtocolMessage, destinations: List[str]):
        """Deliver message with load balancing"""
        # Select destination with lowest load
        # This would require querying agent registry for load information
        # For now, just deliver to the first destination
        if destinations:
            await self._deliver_to_destination(message, destinations[0])
    
    async def _deliver_to_destination(self, message: ProtocolMessage, destination: str):
        """Deliver message to a specific destination"""
        try:
            # Update delivery status
            delivery_key = f"{message.message_id}:{destination}"
            if delivery_key in self.delivery_status:
                self.delivery_status[delivery_key].attempts += 1
                self.delivery_status[delivery_key].last_attempt = datetime.utcnow()
            
            # Send message directly to destination
            target_channel = f"agent:{destination}"
            
            # Modify message for direct delivery
            delivery_message = ProtocolMessage(
                message_id=f"{message.message_id}_delivery_{uuid.uuid4().hex[:8]}",
                sender_id="router",
                recipient_id=destination,
                channel=target_channel,
                message_type=message.message_type,
                title=f"[ROUTED] {message.title}",
                content=message.content,
                payload=message.payload,
                correlation_id=message.message_id,
                priority=message.priority,
                requires_acknowledgment=True
            )
            
            await self.redis.publish(delivery_message)
            
        except Exception as e:
            self.logger.error(f"Failed to deliver to {destination}: {e}")
            await self.acknowledge_delivery(message.message_id, destination, False, str(e))
    
    async def _find_destinations(self, message: ProtocolMessage) -> List[str]:
        """Find destinations for a message based on rules and metadata"""
        destinations = []
        
        # Look for explicit recipient
        if message.recipient_id:
            destinations.append(message.recipient_id)
        
        # Check routing rules
        for rule in self.routing_rules.values():
            if await self._rule_matches(rule, message):
                if rule.destination not in destinations:
                    destinations.append(rule.destination)
        
        return destinations
    
    async def _rule_matches(self, rule: RoutingRule, message: ProtocolMessage) -> bool:
        """Check if a routing rule matches a message"""
        # Check if rule is enabled
        if not rule.enabled:
            return False
        
        # Check pattern matching (simplified)
        if rule.pattern == message.channel:
            return True
        
        # Check message type
        if rule.pattern == message.message_type.value:
            return True
        
        # Check filters
        for key, value in rule.filters.items():
            if key in message.payload:
                if message.payload[key] != value:
                    return False
        
        return False
    
    async def _apply_routing_rules(self, route: MessageRoute, message: ProtocolMessage):
        """Apply routing rules to modify route properties"""
        for rule in self.routing_rules.values():
            if await self._rule_matches(rule, message):
                # Update priority
                if rule.priority.value > route.priority.value:
                    route.priority = rule.priority
                
                # Update strategy
                route.strategy = rule.strategy
                
                # Update delivery guarantee
                route.delivery_guarantee = rule.delivery_guarantee
                
                # Add destination if not already present
                if rule.destination not in route.destinations:
                    route.destinations.append(rule.destination)
    
    async def _retry_message(self, message_id: str, route: MessageRoute):
        """Retry failed message delivery"""
        if route.retries >= 5:  # Max retries
            # Move to dead letter queue
            self.dead_letter_queue.append({
                'message_id': message_id,
                'route': route,
                'failed_at': datetime.utcnow(),
                'reason': 'max_retries_exceeded'
            })
            
            self.logger.error(f"Message {message_id} moved to dead letter queue")
            return
        
        # Schedule retry
        route.retries += 1
        retry_delay = self.retry_intervals.get(route.retries, 60)
        
        async def retry_delivery():
            await asyncio.sleep(retry_delay)
            
            # Re-enqueue message for delivery
            message_data = await self._get_message_data(message_id)
            if message_data:
                self.priority_queues[route.priority].append((message_data, route))
        
        task = asyncio.create_task(retry_delivery())
        self.retry_queue[message_id] = task
        
        self.stats['messages_retried'] += 1
        self.logger.info(f"Retrying message {message_id} (attempt {route.retries})")
    
    async def _get_message_data(self, message_id: str) -> Optional[ProtocolMessage]:
        """Get message data from Redis"""
        try:
            message_key = f"message:{message_id}"
            message_json = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.get(message_key)
            )
            
            if message_json:
                return ProtocolMessage.from_dict(json.loads(message_json))
            
        except Exception as e:
            self.logger.error(f"Failed to get message data for {message_id}: {e}")
        
        return None
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages and routes"""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
                current_time = datetime.utcnow()
                
                # Remove expired routes
                expired_routes = []
                for message_id, route in self.active_routes.items():
                    age = (current_time - route.created_at).seconds
                    if age > 3600:  # 1 hour
                        expired_routes.append(message_id)
                
                for message_id in expired_routes:
                    del self.active_routes[message_id]
                
                # Clean up delivery status
                expired_deliveries = []
                for key, status in self.delivery_status.items():
                    if status.acknowledged_at:
                        age = (current_time - status.acknowledged_at).seconds
                        if age > 1800:  # 30 minutes
                            expired_deliveries.append(key)
                
                for key in expired_deliveries:
                    del self.delivery_status[key]
                
                if expired_routes or expired_deliveries:
                    self.logger.info(f"Cleaned up {len(expired_routes)} routes and {len(expired_deliveries)} delivery statuses")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
    
    async def _load_routing_rules(self):
        """Load routing rules from Redis"""
        try:
            rule_keys = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.keys("routing_rule:*")
            )
            
            for rule_key in rule_keys:
                rule_json = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.get(rule_key)
                )
                
                if rule_json:
                    rule_data = json.loads(rule_json)
                    rule = RoutingRule(**rule_data)
                    self.routing_rules[rule.rule_id] = rule
            
            self.logger.info(f"Loaded {len(self.routing_rules)} routing rules")
            
        except Exception as e:
            self.logger.error(f"Failed to load routing rules: {e}")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        with self.router_lock:
            # Calculate queue sizes
            queue_sizes = {priority.name: len(queue) for priority, queue in self.priority_queues.items()}
            
            # Calculate delivery success rate
            total_attempts = len(self.delivery_status)
            successful_deliveries = sum(
                1 for status in self.delivery_status.values()
                if status.status == MessageStatus.ACKNOWLEDGED
            )
            success_rate = (successful_deliveries / total_attempts) if total_attempts > 0 else 0.0
            
            return {
                'active_routes': len(self.active_routes),
                'delivery_statuses': len(self.delivery_status),
                'routing_rules': len(self.routing_rules),
                'dead_letter_queue_size': len(self.dead_letter_queue),
                'priority_queues': queue_sizes,
                'statistics': self.stats.copy(),
                'success_rate': success_rate,
                'retry_queue_size': len(self.retry_queue)
            }


class MessageDeliveryMonitor:
    """Monitor message delivery and handle timeouts"""
    
    def __init__(self, router: MessageRouter):
        self.router = router
        self.timeout_handlers: Dict[str, Callable] = {}
        self.delivery_timeouts: Dict[str, asyncio.Task] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def start_monitoring(self):
        """Start delivery monitoring"""
        asyncio.create_task(self._monitor_delivery_timeouts())
        self.logger.info("Message delivery monitoring started")
    
    async def monitor_message_delivery(self, message_id: str, timeout_seconds: int = 30):
        """Monitor delivery of a specific message"""
        async def check_timeout():
            await asyncio.sleep(timeout_seconds)
            
            # Check if message is still pending
            route = self.router.active_routes.get(message_id)
            if route and route.status == "pending":
                # Trigger timeout handler
                handler = self.timeout_handlers.get(message_id)
                if handler:
                    try:
                        await handler(message_id)
                    except Exception as e:
                        self.logger.error(f"Timeout handler error: {e}")
                
                # Mark as failed
                route.status = "timeout"
                self.router.stats['messages_failed'] += 1
                
                self.logger.warning(f"Message {message_id} delivery timeout")
        
        task = asyncio.create_task(check_timeout())
        self.delivery_timeouts[message_id] = task
    
    def register_timeout_handler(self, message_id: str, handler: Callable[[str], None]):
        """Register timeout handler for a message"""
        self.timeout_handlers[message_id] = handler
    
    async def _monitor_delivery_timeouts(self):
        """Monitor delivery timeouts"""
        while True:
            try:
                await asyncio.sleep(1)
                
                # Clean up completed timeouts
                completed_timeouts = [
                    message_id for message_id, task in self.delivery_timeouts.items()
                    if task.done()
                ]
                
                for message_id in completed_timeouts:
                    del self.delivery_timeouts[message_id]
                    self.timeout_handlers.pop(message_id, None)
                
            except Exception as e:
                self.logger.error(f"Error in delivery timeout monitor: {e}")
                await asyncio.sleep(5)


# Example usage and default configurations
async def create_default_router(redis_config: Dict[str, Any]) -> MessageRouter:
    """Create a message router with default configuration"""
    redis_client = RedisPubSubClient(**redis_config)
    await redis_client.connect()
    
    router = MessageRouter(redis_client)
    await router.start()
    
    # Add default routing rules
    default_rules = [
        RoutingRule(
            rule_id="trade_signals_to_traders",
            pattern="trading",
            destination="trader_agents",
            priority=MessagePriority.HIGH,
            strategy=RoutingStrategy.FANOUT,
            delivery_guarantee=DeliveryGuarantee.AT_LEAST_ONCE
        ),
        RoutingRule(
            rule_id="alerts_to_handlers",
            pattern="alerts",
            destination="alert_handlers",
            priority=MessagePriority.CRITICAL,
            strategy=RoutingStrategy.BROADCAST,
            delivery_guarantee=DeliveryGuarantee.EXACTLY_ONCE
        )
    ]
    
    for rule in default_rules:
        await router.add_routing_rule(rule)
    
    return router