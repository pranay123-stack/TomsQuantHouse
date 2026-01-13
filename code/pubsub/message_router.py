"""
Message routing system with priority handling and delivery guarantees.
Provides intelligent routing, load balancing, and message delivery optimization.
"""

from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import uuid
import json
import heapq
from collections import defaultdict, deque
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import logging

from schemas.message_schemas import (
    BaseMessage, MessageType, Priority, DeliveryGuarantee,
    MessageMetadata
)

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Message routing strategies"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    RANDOM = "random"
    PRIORITY_BASED = "priority_based"
    AFFINITY_BASED = "affinity_based"


class DeliveryStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


@dataclass
class Route:
    """Message route definition"""
    route_id: str
    source: str
    destination: str
    priority: Priority
    delivery_guarantee: DeliveryGuarantee
    timeout: Optional[int] = None
    max_retries: int = 3
    load_balancer: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    enabled: bool = True
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DeliveryRecord:
    """Record of message delivery attempt"""
    message_id: str
    route_id: str
    status: DeliveryStatus
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    response_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class MessageQueue:
    """Priority message queue"""
    high_priority: List[Tuple[float, int, BaseMessage]] = field(default_factory=list)
    normal_priority: List[Tuple[float, int, BaseMessage]] = field(default_factory=list)
    low_priority: List[Tuple[float, int, BaseMessage]] = field(default_factory=list)
    message_counter: int = 0
    
    def put(self, message: BaseMessage, priority: Priority):
        """Add message to appropriate priority queue"""
        self.message_counter += 1
        
        if priority == Priority.CRITICAL or priority == Priority.EMERGENCY:
            heapq.heappush(self.high_priority, (time.time(), self.message_counter, message))
        elif priority == Priority.NORMAL:
            heapq.heappush(self.normal_priority, (time.time(), self.message_counter, message))
        else:  # LOW
            heapq.heappush(self.low_priority, (time.time(), self.message_counter, message))
    
    def get(self) -> Optional[BaseMessage]:
        """Get next message from highest priority queue"""
        if self.high_priority:
            _, _, message = heapq.heappop(self.high_priority)
            return message
        elif self.normal_priority:
            _, _, message = heapq.heappop(self.normal_priority)
            return message
        elif self.low_priority:
            _, _, message = heapq.heappop(self.low_priority)
            return message
        return None
    
    def qsize(self) -> int:
        """Get total queue size"""
        return len(self.high_priority) + len(self.normal_priority) + len(self.low_priority)
    
    def empty(self) -> bool:
        """Check if queue is empty"""
        return self.qsize() == 0


class LoadBalancer:
    """Load balancer for routing messages across multiple destinations"""
    
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.destinations: Dict[str, Dict[str, Any]] = {}
        self.connection_counters: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.selection_history: deque = deque(maxlen=1000)
        self.weights: Dict[str, float] = {}
        self.affinity_map: Dict[str, str] = {}
    
    def add_destination(self, destination_id: str, weight: float = 1.0, **kwargs):
        """Add destination to load balancer"""
        self.destinations[destination_id] = {
            'id': destination_id,
            'active': True,
            'connections': 0,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'metadata': kwargs
        }
        self.weights[destination_id] = weight
    
    def remove_destination(self, destination_id: str):
        """Remove destination from load balancer"""
        self.destinations.pop(destination_id, None)
        self.weights.pop(destination_id, None)
        self.connection_counters.pop(destination_id, None)
        self.response_times.pop(destination_id, None)
        self.affinity_map.pop(destination_id, None)
    
    def select_destination(self, message: BaseMessage, affinity_key: Optional[str] = None) -> Optional[str]:
        """Select destination based on routing strategy"""
        if not self.destinations:
            return None
        
        # Check affinity first
        if affinity_key and affinity_key in self.affinity_map:
            affinity_dest = self.affinity_map[affinity_key]
            if affinity_dest in self.destinations and self.destinations[affinity_dest]['active']:
                return affinity_dest
        
        # Apply routing strategy
        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_select()
        elif self.strategy == RoutingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select()
        elif self.strategy == RoutingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select()
        elif self.strategy == RoutingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_select()
        elif self.strategy == RoutingStrategy.RANDOM:
            return self._random_select()
        elif self.strategy == RoutingStrategy.PRIORITY_BASED:
            return self._priority_based_select(message)
        else:
            return self._round_robin_select()
    
    def set_affinity(self, affinity_key: str, destination_id: str):
        """Set affinity mapping"""
        self.affinity_map[affinity_key] = destination_id
    
    def update_destination_stats(self, destination_id: str, success: bool, response_time: float):
        """Update destination statistics"""
        if destination_id not in self.destinations:
            return
        
        dest = self.destinations[destination_id]
        dest['total_requests'] += 1
        dest['total_response_time'] += response_time
        
        if success:
            dest['successful_requests'] += 1
        else:
            dest['failed_requests'] += 1
        
        # Update response time tracking
        self.response_times[destination_id].append(response_time)
    
    def get_destination_stats(self, destination_id: str) -> Dict[str, Any]:
        """Get statistics for destination"""
        return self.destinations.get(destination_id, {}).copy()
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all destinations"""
        return {k: v.copy() for k, v in self.destinations.items()}
    
    def _round_robin_select(self) -> Optional[str]:
        """Round robin selection"""
        active_destinations = [d_id for d_id, dest in self.destinations.items() if dest['active']]
        if not active_destinations:
            return None
        
        if len(self.selection_history) == 0:
            selected = active_destinations[0]
        else:
            last_selected = self.selection_history[-1]
            if last_selected in active_destinations:
                current_index = active_destinations.index(last_selected)
                selected = active_destinations[(current_index + 1) % len(active_destinations)]
            else:
                selected = active_destinations[0]
        
        self.selection_history.append(selected)
        return selected
    
    def _weighted_round_robin_select(self) -> Optional[str]:
        """Weighted round robin selection"""
        active_destinations = [(d_id, self.weights.get(d_id, 1.0)) 
                             for d_id, dest in self.destinations.items() if dest['active']]
        
        if not active_destinations:
            return None
        
        # Calculate cumulative weights
        total_weight = sum(weight for _, weight in active_destinations)
        if total_weight == 0:
            return self._round_robin_select()
        
        # Generate random number
        import random
        random_weight = random.uniform(0, total_weight)
        
        # Find destination
        current_weight = 0
        for dest_id, weight in active_destinations:
            current_weight += weight
            if current_weight >= random_weight:
                self.selection_history.append(dest_id)
                return dest_id
        
        # Fallback
        return active_destinations[0][0]
    
    def _least_connections_select(self) -> Optional[str]:
        """Select destination with least connections"""
        active_destinations = [(d_id, dest['connections']) 
                             for d_id, dest in self.destinations.items() if dest['active']]
        
        if not active_destinations:
            return None
        
        # Return destination with minimum connections
        min_connections = min(connections for _, connections in active_destinations)
        min_dests = [dest_id for dest_id, connections in active_destinations if connections == min_connections]
        
        selected = min_dests[0] if len(min_dests) == 1 else self._random_select_dest(min_dests)
        self.selection_history.append(selected)
        return selected
    
    def _least_response_time_select(self) -> Optional[str]:
        """Select destination with least response time"""
        active_destinations = [d_id for d_id, dest in self.destinations.items() if dest['active']]
        
        if not active_destinations:
            return None
        
        # Calculate average response times
        avg_response_times = {}
        for dest_id in active_destinations:
            response_times = list(self.response_times[dest_id])
            if response_times:
                avg_response_times[dest_id] = sum(response_times) / len(response_times)
            else:
                avg_response_times[dest_id] = 0.0
        
        # Return destination with minimum response time
        min_response_time = min(avg_response_times.values())
        fastest_dest = [dest_id for dest_id, time in avg_response_times.items() if time == min_response_time]
        
        selected = fastest_dest[0] if len(fastest_dest) == 1 else self._random_select_dest(fastest_dest)
        self.selection_history.append(selected)
        return selected
    
    def _random_select(self) -> Optional[str]:
        """Random selection"""
        active_destinations = [d_id for d_id, dest in self.destinations.items() if dest['active']]
        
        if not active_destinations:
            return None
        
        import random
        selected = random.choice(active_destinations)
        self.selection_history.append(selected)
        return selected
    
    def _priority_based_select(self, message: BaseMessage) -> Optional[str]:
        """Priority-based selection considering message type and content"""
        # High priority messages get better destinations
        if message.metadata.priority in [Priority.CRITICAL, Priority.EMERGENCY]:
            # Use least response time for critical messages
            return self._least_response_time_select()
        elif message.metadata.priority == Priority.HIGH:
            # Use least connections for high priority
            return self._least_connections_select()
        else:
            # Use round robin for normal/low priority
            return self._round_robin_select()
    
    def _random_select_dest(self, destinations: List[str]) -> str:
        """Random selection from given destinations"""
        import random
        return random.choice(destinations)


class MessageRouter:
    """Core message router with priority handling and delivery guarantees"""
    
    def __init__(self, router_id: str):
        self.router_id = router_id
        self.routes: Dict[str, Route] = {}
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.message_queues: Dict[str, MessageQueue] = defaultdict(MessageQueue)
        self.delivery_records: Dict[str, DeliveryRecord] = {}
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.routing_rules: List[Callable] = []
        self.delivery_callbacks: Dict[str, Callable] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.running = False
        self.router_lock = threading.RLock()
        
        # Performance metrics
        self.metrics = {
            'messages_routed': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'average_latency': 0.0,
            'routing_errors': 0,
            'start_time': datetime.now()
        }
    
    def start(self):
        """Start the message router"""
        self.running = True
        self._start_delivery_workers()
        logger.info(f"Message router {self.router_id} started")
    
    def stop(self):
        """Stop the message router"""
        self.running = False
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info(f"Message router {self.router_id} stopped")
    
    def add_route(self, route: Route):
        """Add a message route"""
        with self.router_lock:
            self.routes[route.route_id] = route
            
            # Create load balancer for route if needed
            if route.destination not in self.load_balancers:
                self.load_balancers[route.destination] = LoadBalancer(route.load_balancer)
    
    def remove_route(self, route_id: str):
        """Remove a message route"""
        with self.router_lock:
            route = self.routes.pop(route_id, None)
            if route and self.load_balancers.get(route.destination):
                # Check if any other routes use this destination
                destinations_used = [r for r in self.routes.values() if r.destination == route.destination]
                if not destinations_used:
                    del self.load_balancers[route.destination]
    
    def add_destination(self, route_id: str, destination_id: str, weight: float = 1.0, **kwargs):
        """Add destination to route's load balancer"""
        if route_id in self.routes:
            route = self.routes[route_id]
            if route.destination in self.load_balancers:
                self.load_balancers[route.destination].add_destination(destination_id, weight, **kwargs)
    
    async def route_message(self, message: BaseMessage, 
                          transport_layer: Optional[Any] = None) -> str:
        """Route a message through the system"""
        start_time = time.time()
        
        try:
            with self.router_lock:
                # Determine route
                route = self._select_route(message)
                if not route:
                    logger.error(f"No route found for message {message.metadata.message_id}")
                    self.metrics['routing_errors'] += 1
                    return ""
                
                # Create delivery record
                delivery_record = DeliveryRecord(
                    message_id=message.metadata.message_id,
                    route_id=route.route_id,
                    status=DeliveryStatus.PENDING
                )
                self.delivery_records[message.metadata.message_id] = delivery_record
                
                # Add to appropriate queue
                queue_key = f"{route.source}:{route.destination}"
                self.message_queues[queue_key].put(message, message.metadata.priority)
            
            # Trigger delivery if transport layer is available
            if transport_layer:
                asyncio.create_task(self._process_queue_delivery(queue_key, transport_layer))
            
            # Update metrics
            self.metrics['messages_routed'] += 1
            routing_time = time.time() - start_time
            
            logger.debug(f"Message {message.metadata.message_id} routed via {route.route_id} in {routing_time:.3f}s")
            return route.route_id
            
        except Exception as e:
            self.metrics['routing_errors'] += 1
            logger.error(f"Error routing message {message.metadata.message_id}: {e}")
            raise
    
    def get_message_status(self, message_id: str) -> Optional[DeliveryRecord]:
        """Get delivery status of a message"""
        return self.delivery_records.get(message_id)
    
    def set_delivery_callback(self, message_id: str, callback: Callable):
        """Set callback for message delivery notification"""
        self.delivery_callbacks[message_id] = callback
    
    def get_router_stats(self) -> Dict[str, Any]:
        """Get router performance statistics"""
        with self.router_lock:
            queue_stats = {
                key: {
                    'size': queue.qsize(),
                    'high_priority': len(queue.high_priority),
                    'normal_priority': len(queue.normal_priority),
                    'low_priority': len(queue.low_priority)
                }
                for key, queue in self.message_queues.items()
            }
            
            delivery_stats = {
                'total_records': len(self.delivery_records),
                'pending': len([r for r in self.delivery_records.values() if r.status == DeliveryStatus.PENDING]),
                'delivered': len([r for r in self.delivery_records.values() if r.status == DeliveryStatus.DELIVERED]),
                'failed': len([r for r in self.delivery_records.values() if r.status == DeliveryStatus.FAILED]),
                'retrying': len([r for r in self.delivery_records.values() if r.status == DeliveryStatus.RETRYING])
            }
            
            uptime = datetime.now() - self.metrics['start_time']
            
            return {
                'router_id': self.router_id,
                'uptime_seconds': uptime.total_seconds(),
                'messages_routed': self.metrics['messages_routed'],
                'messages_delivered': self.metrics['messages_delivered'],
                'messages_failed': self.metrics['messages_failed'],
                'routing_errors': self.metrics['routing_errors'],
                'average_latency': self.metrics['average_latency'],
                'queue_stats': queue_stats,
                'delivery_stats': delivery_stats,
                'active_routes': len(self.routes),
                'load_balancers': len(self.load_balancers)
            }
    
    def _select_route(self, message: BaseMessage) -> Optional[Route]:
        """Select appropriate route for message"""
        # Apply routing rules
        for rule in self.routing_rules:
            route = rule(message)
            if route:
                return route
        
        # Default routing based on message characteristics
        if message.recipient_id:
            # Direct routing to specific recipient
            for route in self.routes.values():
                if route.destination == message.recipient_id and route.enabled:
                    return route
        
        elif message.channel:
            # Channel-based routing
            for route in self.routes.values():
                if route.destination == message.channel and route.enabled:
                    return route
        
        # Fallback to any available route
        for route in self.routes.values():
            if route.enabled:
                return route
        
        return None
    
    def _start_delivery_workers(self):
        """Start background workers for message delivery"""
        for queue_key in self.message_queues:
            thread = threading.Thread(
                target=self._delivery_worker,
                args=(queue_key,),
                daemon=True
            )
            thread.start()
    
    async def _process_queue_delivery(self, queue_key: str, transport_layer: Any):
        """Process messages in queue for delivery"""
        # This would integrate with the actual delivery system
        # For now, it's a placeholder
        pass
    
    def _delivery_worker(self, queue_key: str):
        """Background worker for processing delivery queue"""
        queue = self.message_queues[queue_key]
        
        while self.running:
            try:
                # Get next message from queue
                message = queue.get()
                if message:
                    # Process message delivery
                    asyncio.run(self._deliver_message(message, queue_key))
                else:
                    # No messages, wait a bit
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in delivery worker for queue {queue_key}: {e}")
                time.sleep(1)
    
    async def _deliver_message(self, message: BaseMessage, queue_key: str):
        """Deliver a single message"""
        delivery_record = self.delivery_records.get(message.metadata.message_id)
        if not delivery_record:
            return
        
        try:
            delivery_record.status = DeliveryStatus.IN_TRANSIT
            delivery_record.attempts += 1
            delivery_record.last_attempt = datetime.now()
            
            # Simulate delivery (replace with actual transport call)
            success = await self._simulate_delivery(message)
            
            if success:
                delivery_record.status = DeliveryStatus.DELIVERED
                self.metrics['messages_delivered'] += 1
                
                # Call delivery callback if set
                callback = self.delivery_callbacks.get(message.metadata.message_id)
                if callback:
                    try:
                        callback(message, True, None)
                    except Exception as e:
                        logger.error(f"Error in delivery callback: {e}")
            else:
                # Handle delivery failure
                await self._handle_delivery_failure(delivery_record)
            
        except Exception as e:
            logger.error(f"Error delivering message {message.metadata.message_id}: {e}")
            delivery_record.status = DeliveryStatus.FAILED
            delivery_record.error_message = str(e)
            self.metrics['messages_failed'] += 1
    
    async def _simulate_delivery(self, message: BaseMessage) -> bool:
        """Simulate message delivery (placeholder for actual transport)"""
        # This is a placeholder - replace with actual transport implementation
        await asyncio.sleep(0.01)  # Simulate network delay
        return True  # Always succeed for simulation
    
    async def _handle_delivery_failure(self, delivery_record: DeliveryRecord):
        """Handle delivery failure and retry logic"""
        route = self.routes.get(delivery_record.route_id)
        if not route:
            delivery_record.status = DeliveryStatus.FAILED
            return
        
        if delivery_record.attempts < route.max_retries:
            # Schedule retry
            delivery_record.status = DeliveryStatus.RETRYING
            retry_delay = min(2 ** delivery_record.attempts, 60)  # Exponential backoff, max 60s
            delivery_record.next_retry = datetime.now() + timedelta(seconds=retry_delay)
            
            # Add back to queue
            queue_key = f"{route.source}:{route.destination}"
            # Note: This would need the original message, which we don't have in this context
            # In a real implementation, you'd store the message with the delivery record
        else:
            # Max retries exceeded
            delivery_record.status = DeliveryStatus.FAILED
            self.metrics['messages_failed'] += 1
    
    def add_routing_rule(self, rule: Callable[[BaseMessage], Optional[Route]]):
        """Add custom routing rule"""
        self.routing_rules.append(rule)


# Priority-based routing rules
def priority_based_routing_rule(message: BaseMessage) -> Optional[Route]:
    """Route messages based on priority and content"""
    # High priority messages get dedicated routes
    if message.metadata.priority in [Priority.CRITICAL, Priority.EMERGENCY]:
        return Route(
            route_id=f"high_priority_{message.metadata.message_id}",
            source="router",
            destination="high_priority_queue",
            priority=message.metadata.priority,
            delivery_guarantee=message.metadata.delivery_guarantee
        )
    
    return None


def content_based_routing_rule(message: BaseMessage) -> Optional[Route]:
    """Route messages based on content"""
    if isinstance(message.payload, dict):
        # Route trading signals to trading channels
        if 'symbol' in message.payload:
            return Route(
                route_id=f"symbol_{message.payload['symbol']}",
                source="router",
                destination=f"trading_{message.payload['symbol']}",
                priority=message.metadata.priority,
                delivery_guarantee=message.metadata.delivery_guarantee
            )
    
    return None


# Example usage and configuration
def create_router_with_default_config(router_id: str) -> MessageRouter:
    """Create router with default configuration"""
    router = MessageRouter(router_id)
    
    # Add default routes
    high_priority_route = Route(
        route_id="high_priority",
        source="*",
        destination="high_priority_queue",
        priority=Priority.HIGH,
        delivery_guarantee=DeliveryGuarantee.AT_LEAST_ONCE,
        load_balancer=RoutingStrategy.LEAST_RESPONSE_TIME
    )
    
    normal_route = Route(
        route_id="normal",
        source="*", 
        destination="normal_queue",
        priority=Priority.NORMAL,
        delivery_guarantee=DeliveryGuarantee.BEST_EFFORT,
        load_balancer=RoutingStrategy.ROUND_ROBIN
    )
    
    router.add_route(high_priority_route)
    router.add_route(normal_route)
    
    # Add routing rules
    router.add_routing_rule(priority_based_routing_rule)
    router.add_routing_rule(content_based_routing_rule)
    
    return router