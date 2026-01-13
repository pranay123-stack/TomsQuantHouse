"""
Agent Discovery and Registration System
Manages agent registration, discovery, and health monitoring using Redis
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable
from dataclasses import asdict
import hashlib
import uuid
import logging
import weakref
from collections import defaultdict, deque
import threading
import time

from core.redis_client import RedisPubSubClient, AgentType, MessagePriority
from protocols.message_schemas import (
    ProtocolMessage, MessageType, MessageStatus, AgentMetadata,
    MessageFactory
)


class AgentStatus(Enum):
    """Agent status states"""
    REGISTERED = "registered"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DiscoveryScope(Enum):
    """Discovery scope types"""
    LOCAL = "local"
    CLUSTER = "cluster"
    NETWORK = "network"
    GLOBAL = "global"


class AgentCapability:
    """Agent capability definition"""
    def __init__(self, name: str, version: str = "1.0", description: str = "", 
                 parameters: Dict[str, Any] = None, dependencies: List[str] = None):
        self.name = name
        self.version = version
        self.description = description
        self.parameters = parameters or {}
        self.dependencies = dependencies or []


class AgentHealth:
    """Agent health information"""
    def __init__(self, agent_id: str, status: AgentStatus, last_heartbeat: datetime,
                 cpu_usage: float = 0.0, memory_usage: float = 0.0, active_connections: int = 0,
                 messages_processed: int = 0, error_rate: float = 0.0, 
                 response_time_avg: float = 0.0, uptime: timedelta = None):
        self.agent_id = agent_id
        self.status = status
        self.last_heartbeat = last_heartbeat
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.active_connections = active_connections
        self.messages_processed = messages_processed
        self.error_rate = error_rate
        self.response_time_avg = response_time_avg
        self.uptime = uptime or timedelta(0)


class DiscoveryQuery:
    """Agent discovery query"""
    def __init__(self, query_id: str, requester_id: str, criteria: Dict[str, Any],
                 scope: DiscoveryScope = DiscoveryScope.LOCAL, timeout: int = 30,
                 max_results: int = 100, created_at: datetime = None,
                 results: List[AgentMetadata] = None, status: str = "pending"):
        self.query_id = query_id
        self.requester_id = requester_id
        self.criteria = criteria
        self.scope = scope
        self.timeout = timeout
        self.max_results = max_results
        self.created_at = created_at or datetime.utcnow()
        self.results = results or []
        self.status = status


class ClusterInfo:
    """Cluster information for distributed agent management"""
    def __init__(self, cluster_id: str, cluster_name: str, 
                 nodes: Dict[str, Dict[str, Any]] = None, leader_id: Optional[str] = None,
                 created_at: datetime = None, last_heartbeat: datetime = None):
        self.cluster_id = cluster_id
        self.cluster_name = cluster_name
        self.nodes = nodes or {}
        self.leader_id = leader_id
        self.created_at = created_at or datetime.utcnow()
        self.last_heartbeat = last_heartbeat or datetime.utcnow()


logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for agent discovery and registration using Redis"""
    
    def __init__(self, redis_client: RedisPubSubClient):
        self.redis = redis_client
        self.registered_agents: Dict[str, AgentMetadata] = {}
        self.agent_health: Dict[str, AgentHealth] = {}
        self.agent_capabilities: Dict[str, List[AgentCapability]] = defaultdict(list)
        self.agent_connections: Dict[str, Set[str]] = defaultdict(set)
        self.regions: Dict[str, Set[str]] = defaultdict(set)  # region -> agent_ids
        self.tags: Dict[str, Set[str]] = defaultdict(set)  # tag -> agent_ids
        self.discovery_handlers: List[Callable] = []
        
        # Redis keys
        self.agents_hash_key = "agents:registry"
        self.agent_heartbeat_key = "agents:heartbeats"
        self.agent_capabilities_index = "agents:capabilities"
        self.agent_types_index = "agents:types"
        
        # Registration tracking
        self.registration_history: deque = deque(maxlen=10000)
        self.heartbeat_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Thread safety
        self.registry_lock = threading.RLock()
        
        # Configuration
        self.heartbeat_timeout = 30  # seconds
        self.cleanup_interval = 60  # seconds
        
        # Statistics
        self.stats = {
            'total_registrations': 0,
            'active_agents': 0,
            'total_messages': 0,
            'discovery_queries': 0,
            'failed_registrations': 0
        }
    
    async def start(self):
        """Start the agent registry service"""
        # Load existing agents from Redis
        await self._load_agents_from_redis()
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_monitor())
        asyncio.create_task(self._cleanup_expired_agents())
        
        self.logger.info("Agent registry service started")
    
    async def stop(self):
        """Stop the agent registry service"""
        self.logger.info("Agent registry service stopped")
    
    async def register_agent(self, agent_metadata: AgentMetadata) -> bool:
        """Register an agent in the system"""
        try:
            # Initialize health tracking
            if agent_metadata.agent_id not in self.agent_health:
                self.agent_health[agent_metadata.agent_id] = AgentHealth(
                    agent_id=agent_metadata.agent_id,
                    status=AgentStatus.REGISTERED,
                    last_heartbeat=datetime.utcnow()
                )
            
            # Store in Redis
            agent_key = f"agent:{agent_metadata.agent_id}"
            agent_data = asdict(agent_metadata)
            agent_data['last_heartbeat'] = datetime.utcnow().isoformat()
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.hset(
                    self.agents_hash_key,
                    agent_metadata.agent_id,
                    json.dumps(agent_data)
                )
            )
            
            # Store full agent data
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.setex(
                    agent_key,
                    3600,  # 1 hour expiration
                    json.dumps(agent_data)
                )
            )
            
            # Update indexes
            await self._update_indexes(agent_metadata)
            
            # Update local registry
            self.registered_agents[agent_metadata.agent_id] = agent_metadata
            
            # Track registration
            self.registration_history.append({
                'agent_id': agent_metadata.agent_id,
                'timestamp': datetime.utcnow(),
                'action': 'registered'
            })
            
            self.stats['total_registrations'] += 1
            self._update_active_agents_count()
            
            # Broadcast registration
            registration_msg = MessageFactory.create_agent_registration(agent_metadata)
            await self.redis.publish(registration_msg)
            
            self.logger.info(f"Agent {agent_metadata.agent_id} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_metadata.agent_id}: {e}")
            self.stats['failed_registrations'] += 1
            return False
    
    async def unregister_agent(self, agent_id: str, reason: str = "unregister") -> bool:
        """Unregister an agent from the system"""
        try:
            # Remove from local registry
            if agent_id in self.registered_agents:
                agent_metadata = self.registered_agents.pop(agent_id)
            
            # Remove health data
            if agent_id in self.agent_health:
                del self.agent_health[agent_id]
            
            # Remove from Redis
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.hdel(self.agents_hash_key, agent_id)
            )
            
            # Remove full agent data
            agent_key = f"agent:{agent_id}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.delete(agent_key)
            )
            
            # Remove from indexes
            await self._remove_from_indexes(agent_id)
            
            # Track unregistration
            self.registration_history.append({
                'agent_id': agent_id,
                'timestamp': datetime.utcnow(),
                'action': 'unregistered',
                'reason': reason
            })
            
            self._update_active_agents_count()
            
            self.logger.info(f"Agent {agent_id} unregistered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def discover_agents(self, criteria: Dict[str, Any], 
                            scope: DiscoveryScope = DiscoveryScope.LOCAL) -> List[AgentMetadata]:
        """Discover agents matching criteria"""
        discovered_agents = []
        
        try:
            for agent_id, agent_metadata in self.registered_agents.items():
                if self._matches_criteria(agent_metadata, agent_id, criteria):
                    # Check if agent is healthy (optional)
                    if criteria.get('healthy_only', False):
                        health = self.agent_health.get(agent_id)
                        if not health or health.status not in [AgentStatus.ACTIVE, AgentStatus.IDLE]:
                            continue
                    
                    discovered_agents.append(agent_metadata)
            
            # Apply limits
            max_results = criteria.get('max_results', 100)
            if len(discovered_agents) > max_results:
                discovered_agents = discovered_agents[:max_results]
            
            self.stats['discovery_queries'] += 1
            self.logger.debug(f"Discovered {len(discovered_agents)} agents matching criteria: {criteria}")
            return discovered_agents
            
        except Exception as e:
            self.logger.error(f"Error during agent discovery: {e}")
            return []
    
    def get_agent_info(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get information about a specific agent"""
        with self.registry_lock:
            return self.registered_agents.get(agent_id)
    
    def get_agent_health(self, agent_id: str) -> Optional[AgentHealth]:
        """Get health information for a specific agent"""
        with self.registry_lock:
            return self.agent_health.get(agent_id)
    
    async def update_heartbeat(self, agent_id: str, health_data: Dict[str, Any]) -> bool:
        """Update agent heartbeat and health information"""
        try:
            if agent_id not in self.registered_agents:
                self.logger.warning(f"Heartbeat from unknown agent {agent_id}")
                return False
            
            # Update health information
            health = self.agent_health[agent_id]
            health.last_heartbeat = datetime.utcnow()
            health.status = AgentStatus.ACTIVE
            
            # Update metrics
            if 'cpu_usage' in health_data:
                health.cpu_usage = health_data['cpu_usage']
            if 'memory_usage' in health_data:
                health.memory_usage = health_data['memory_usage']
            if 'active_connections' in health_data:
                health.active_connections = health_data['active_connections']
            if 'messages_processed' in health_data:
                health.messages_processed = health_data['messages_processed']
            if 'error_rate' in health_data:
                health.error_rate = health_data['error_rate']
            if 'response_time_avg' in health_data:
                health.response_time_avg = health_data['response_time_avg']
            
            # Calculate uptime
            agent_metadata = self.registered_agents[agent_id]
            health.uptime = datetime.utcnow() - agent_metadata.last_heartbeat
            
            # Track heartbeat
            self.heartbeat_history[agent_id].append({
                'timestamp': health.last_heartbeat,
                'status': health.status,
                'data': health_data
            })
            
            # Update agent metadata with latest info
            agent_metadata.last_heartbeat = datetime.utcnow()
            
            # Store in Redis
            heartbeat_key = f"heartbeat:{agent_id}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.setex(
                    heartbeat_key,
                    300,  # 5 minutes expiration
                    json.dumps(health_data, default=str)
                )
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update heartbeat for agent {agent_id}: {e}")
            return False
    
    async def _load_agents_from_redis(self):
        """Load agent registry from Redis"""
        try:
            agents_data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.hgetall(self.agents_hash_key)
            )
            
            for agent_id, agent_data_json in agents_data.items():
                try:
                    agent_data = json.loads(agent_data_json)
                    
                    # Parse last heartbeat
                    if 'last_heartbeat' in agent_data and agent_data['last_heartbeat']:
                        agent_data['last_heartbeat'] = datetime.fromisoformat(
                            agent_data['last_heartbeat']
                        )
                    else:
                        agent_data['last_heartbeat'] = datetime.utcnow()
                    
                    agent_metadata = AgentMetadata(**agent_data)
                    self.registered_agents[agent_id] = agent_metadata
                    
                    # Initialize health
                    self.agent_health[agent_id] = AgentHealth(
                        agent_id=agent_id,
                        status=AgentStatus.ACTIVE,
                        last_heartbeat=agent_metadata.last_heartbeat
                    )
                    
                except Exception as e:
                    self.logger.error(f"Failed to parse agent data for {agent_id}: {e}")
            
            self.logger.info(f"Loaded {len(self.registered_agents)} agents from Redis")
            
        except Exception as e:
            self.logger.error(f"Failed to load agents from Redis: {e}")
    
    async def _update_indexes(self, agent_metadata: AgentMetadata):
        """Update search indexes"""
        try:
            # Update capabilities index
            for capability in agent_metadata.capabilities:
                capability_key = f"capability:{capability}"
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.sadd(capability_key, agent_metadata.agent_id)
                )
            
            # Update types index
            type_key = f"type:{agent_metadata.agent_type}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.sadd(type_key, agent_metadata.agent_id)
            )
            
            # Update symbols index
            for symbol in agent_metadata.supported_symbols:
                symbol_key = f"symbol:{symbol}"
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.sadd(symbol_key, agent_metadata.agent_id)
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update indexes for agent {agent_metadata.agent_id}: {e}")
    
    async def _remove_from_indexes(self, agent_id: str):
        """Remove agent from search indexes"""
        try:
            if agent_id not in self.registered_agents:
                return
            
            agent_metadata = self.registered_agents[agent_id]
            
            # Remove from capabilities index
            for capability in agent_metadata.capabilities:
                capability_key = f"capability:{capability}"
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.srem(capability_key, agent_id)
                )
            
            # Remove from types index
            type_key = f"type:{agent_metadata.agent_type}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.srem(type_key, agent_id)
            )
            
            # Remove from symbols index
            for symbol in agent_metadata.supported_symbols:
                symbol_key = f"symbol:{symbol}"
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.srem(symbol_key, agent_id)
                )
                
        except Exception as e:
            self.logger.error(f"Failed to remove from indexes: {e}")
    
    def _matches_criteria(self, agent_metadata: AgentMetadata, agent_id: str, criteria: Dict[str, Any]) -> bool:
        """Check if agent matches discovery criteria"""
        # Check agent type
        if 'agent_type' in criteria and agent_metadata.agent_type != criteria['agent_type']:
            return False
        
        # Check capabilities
        if 'capabilities' in criteria:
            required_caps = criteria['capabilities']
            available_caps = set(agent_metadata.capabilities)
            if not all(cap in available_caps for cap in required_caps):
                return False
        
        # Check version
        if 'min_version' in criteria:
            if agent_metadata.version < criteria['min_version']:
                return False
        
        # Check symbols
        if 'symbols' in criteria:
            required_symbols = criteria['symbols']
            available_symbols = set(agent_metadata.supported_symbols)
            if not any(sym in available_symbols for sym in required_symbols):
                return False
        
        # Check custom metadata
        if 'metadata' in criteria:
            for key, value in criteria['metadata'].items():
                if agent_metadata.metadata.get(key) != value:
                    return False
        
        return True
    
    async def _heartbeat_monitor(self):
        """Monitor agent heartbeats and mark unhealthy agents"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                current_time = datetime.utcnow()
                unhealthy_agents = []
                
                for agent_id, health in self.agent_health.items():
                    time_since_heartbeat = (current_time - health.last_heartbeat).seconds
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        unhealthy_agents.append(agent_id)
                        health.status = AgentStatus.OFFLINE
                
                # Log unhealthy agents
                for agent_id in unhealthy_agents:
                    self.logger.warning(f"Agent {agent_id} marked as unhealthy")
                    # Could broadcast agent offline notification here
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
    
    async def _cleanup_expired_agents(self):
        """Clean up expired agents from registry"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = datetime.utcnow()
                expired_agents = []
                
                for agent_id, health in self.agent_health.items():
                    time_since_heartbeat = (current_time - health.last_heartbeat).seconds
                    
                    if time_since_heartbeat > (self.heartbeat_timeout * 3):
                        expired_agents.append(agent_id)
                
                # Remove expired agents
                for agent_id in expired_agents:
                    self.logger.info(f"Removing expired agent {agent_id}")
                    await self.unregister_agent(agent_id, reason="expired")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
    
    def _update_active_agents_count(self):
        """Update the count of active agents"""
        active_count = sum(1 for health in self.agent_health.values() 
                         if health.status in [AgentStatus.ACTIVE, AgentStatus.IDLE, AgentStatus.BUSY])
        self.stats['active_agents'] = active_count
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self.registry_lock:
            # Count agents by status
            status_counts = defaultdict(int)
            for health in self.agent_health.values():
                status_counts[health.status.value] += 1
            
            # Calculate average response time
            response_times = [h.response_time_avg for h in self.agent_health.values() if h.response_time_avg > 0]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            
            return {
                'total_agents': len(self.registered_agents),
                'active_agents': status_counts.get('active', 0),
                'idle_agents': status_counts.get('idle', 0),
                'busy_agents': status_counts.get('busy', 0),
                'offline_agents': status_counts.get('offline', 0),
                'error_agents': status_counts.get('error', 0),
                'total_capabilities': sum(len(caps) for caps in self.agent_capabilities.values()),
                'total_regions': len(self.regions),
                'total_tags': len(self.tags),
                'avg_response_time': avg_response_time,
                'registration_stats': self.stats.copy(),
                'registration_history_size': len(self.registration_history)
            }


class AgentDiscoveryService:
    """Service for discovering and connecting to agents"""
    
    def __init__(self, agent_registry: AgentRegistry, redis_client: RedisPubSubClient):
        self.registry = agent_registry
        self.redis = redis_client
        self.service_id = f"discovery_service_{uuid.uuid4().hex[:8]}"
        self.active_queries: Dict[str, DiscoveryQuery] = {}
        self.discovery_handlers: Dict[str, Callable] = {}
        self.discovery_cache: Dict[str, List[AgentMetadata]] = {}
        self.cache_ttl = 30  # seconds
        
        # Statistics
        self.discovery_stats = {
            'queries_processed': 0,
            'agents_discovered': 0,
            'average_query_time': 0.0
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the discovery service"""
        await self.registry.start()
        self.logger.info(f"Agent discovery service {self.service_id} started")
    
    async def stop(self):
        """Stop the discovery service"""
        await self.registry.stop()
        self.logger.info(f"Agent discovery service {self.service_id} stopped")
    
    async def discover_trading_agents(self, symbols: List[str] = None) -> List[AgentMetadata]:
        """Discover agents that can handle trading for specified symbols"""
        criteria = {'agent_type': 'trader'}
        if symbols:
            criteria['symbols'] = symbols
        
        return await self.registry.discover_agents(criteria)
    
    async def discover_prediction_agents(self, symbols: List[str] = None) -> List[AgentMetadata]:
        """Discover agents that can provide predictions for specified symbols"""
        criteria = {'agent_type': 'predictor'}
        if symbols:
            criteria['symbols'] = symbols
        
        return await self.registry.discover_agents(criteria)
    
    async def discover_alert_handlers(self, alert_types: List[str] = None) -> List[AgentMetadata]:
        """Discover agents that can handle specific alert types"""
        criteria = {'agent_type': 'alert_handler'}
        if alert_types:
            criteria['capabilities'] = alert_types
        
        return await self.registry.discover_agents(criteria)
    
    async def find_agent_by_capability(self, capability: str) -> Optional[AgentMetadata]:
        """Find an agent with specific capability"""
        agents = await self.registry.discover_agents({'capabilities': [capability]})
        return agents[0] if agents else None
    
    async def get_load_balanced_agent(self, agent_type: str, symbols: List[str] = None) -> Optional[AgentMetadata]:
        """Get an agent with lowest current load"""
        criteria = {'agent_type': agent_type}
        if symbols:
            criteria['symbols'] = symbols
        
        agents = await self.registry.discover_agents(criteria)
        
        if not agents:
            return None
        
        # Sort by current load (ascending)
        agents.sort(key=lambda a: a.current_load)
        
        return agents[0]
    
    async def send_discovery_request(self, requester_id: str, criteria: Dict[str, Any]) -> str:
        """Send a discovery request to the network"""
        discovery_msg = ProtocolMessage(
            sender_id=requester_id,
            channel="agent_discovery",
            message_type=MessageType.AGENT_DISCOVER,
            title="Agent Discovery Request",
            content=json.dumps(criteria),
            priority=3
        )
        
        await self.redis.publish(discovery_msg)
        return discovery_msg.message_id
    
    async def register_discovery_handler(self, handler: Callable[[ProtocolMessage], None]):
        """Register handler for discovery responses"""
        # This would be called when a discovery response is received
        pass
    
    async def handle_discovery_request(self, message: ProtocolMessage) -> Optional[ProtocolMessage]:
        """Handle incoming discovery request"""
        if message.message_type != MessageType.AGENT_DISCOVER:
            return None
        
        try:
            # Parse criteria from message content
            criteria = json.loads(message.content) if message.content else {}
            
            # Perform discovery
            results = await self.registry.discover_agents(criteria)
            
            # Create response message
            response = ProtocolMessage(
                correlation_id=message.message_id,
                sender_id=self.service_id,
                recipient_id=message.sender_id,
                channel=message.channel,
                message_type=MessageType.AGENT_DISCOVER,
                title="Agent Discovery Response",
                content=json.dumps({
                    'query_id': message.message_id,
                    'results': [asdict(agent) for agent in results]
                }),
                priority=2
            )
            
            # Update statistics
            self.discovery_stats['queries_processed'] += 1
            self.discovery_stats['agents_discovered'] += len(results)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error handling discovery request: {e}")
            
            # Return error response
            error_response = ProtocolMessage(
                correlation_id=message.message_id,
                sender_id=self.service_id,
                recipient_id=message.sender_id,
                channel=message.channel,
                message_type=MessageType.ERROR,
                title="Discovery Error",
                content=str(e),
                priority=4
            )
            
            return error_response
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery service statistics"""
        return {
            'service_id': self.service_id,
            'active_queries': len(self.active_queries),
            'discovery_stats': self.discovery_stats.copy(),
            'registry_stats': self.registry.get_registry_stats()
        }


class AgentHealthMonitor:
    """Monitor agent health and availability"""
    
    def __init__(self, agent_registry: AgentRegistry, redis_client: RedisPubSubClient):
        self.registry = agent_registry
        self.redis = redis_client
        self.health_status: Dict[str, Dict[str, Any]] = {}
        self.health_handlers: List[Callable] = []
        self.monitor_running = False
        self.monitor_task = None
        
        self.logger = logging.getLogger(__name__)
    
    async def start_monitoring(self):
        """Start health monitoring"""
        self.monitor_running = True
        self.monitor_task = asyncio.create_task(self._health_monitor_loop())
        self.logger.info("Agent health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitor_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
        self.logger.info("Agent health monitoring stopped")
    
    async def report_health(self, agent_id: str, health_data: Dict[str, Any]):
        """Report agent health status"""
        try:
            health_status = {
                'timestamp': datetime.utcnow(),
                'status': health_data.get('status', 'unknown'),
                'cpu_usage': health_data.get('cpu_usage', 0),
                'memory_usage': health_data.get('memory_usage', 0),
                'active_tasks': health_data.get('active_tasks', 0),
                'error_count': health_data.get('error_count', 0),
                'last_activity': health_data.get('last_activity')
            }
            
            self.health_status[agent_id] = health_status
            
            # Update registry
            await self.registry.update_heartbeat(agent_id, health_data)
            
            # Store in Redis for persistence
            health_key = f"agent_health:{agent_id}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.setex(
                    health_key,
                    300,  # 5 minutes expiration
                    json.dumps(health_status, default=str)
                )
            )
            
            # Notify handlers
            for handler in self.health_handlers:
                try:
                    await handler(agent_id, health_status)
                except Exception as e:
                    self.logger.error(f"Health handler error: {e}")
            
            self.logger.debug(f"Health report received from {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to process health report from {agent_id}: {e}")
    
    async def get_agent_health(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent health status"""
        return self.health_status.get(agent_id)
    
    async def get_all_agents_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all agents"""
        return self.health_status.copy()
    
    async def _health_monitor_loop(self):
        """Background loop for health monitoring"""
        while self.monitor_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.utcnow()
                
                for agent_id, health_data in self.health_status.items():
                    if 'timestamp' in health_data:
                        time_since_update = (current_time - health_data['timestamp']).seconds
                        
                        if time_since_update > 120:  # 2 minutes without update
                            health_data['status'] = 'stale'
                            self.logger.warning(f"Agent {agent_id} health data is stale")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(5)
    
    def register_health_handler(self, handler: Callable[[str, Dict[str, Any]], None]):
        """Register handler for health status changes"""
        self.health_handlers.append(handler)


# Example usage
async def create_default_discovery_service(redis_config: Dict[str, Any]) -> Tuple[AgentRegistry, AgentDiscoveryService, AgentHealthMonitor]:
    """Create default discovery service with registry and health monitor"""
    redis_client = RedisPubSubClient(**redis_config)
    await redis_client.connect()
    
    registry = AgentRegistry(redis_client)
    discovery_service = AgentDiscoveryService(registry, redis_client)
    health_monitor = AgentHealthMonitor(registry, redis_client)
    
    return registry, discovery_service, health_monitor