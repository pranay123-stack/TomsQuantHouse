"""
Agent Communication System - Main Integration Module
Integrates all components: message routing, agent discovery, persistence, events, monitoring, and security.
"""

from typing import Dict, Any, List, Optional, Callable, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import logging
import threading
import time
from pathlib import Path
import weakref
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import all components
from schemas.message_schemas import (
    BaseMessage, MessageType, MessageFactory, AgentInfo, Priority
)
from protocols.communication_protocols import (
    ProtocolOrchestrator, CommunicationPattern, ProtocolFactory
)
from message_router import MessageRouter, RoutingStrategy, create_router_with_default_config
from agents.agent_discovery import AgentRegistry, AgentDiscoveryService, create_default_discovery_service
from message_persistence import MessagePersistor, StorageType, RetentionPolicy, create_default_persistor
from event_architecture import (
    EventBus, CoordinationEngine, WorkflowEngine, Event, EventType,
    EventSeverity, create_default_event_system, create_default_event_handlers
)
from monitoring.analytics import (
    MetricCollector, AlertManager, MessageFlowAnalyzer, MonitoringDashboard,
    create_monitoring_system, AlertSeverity
)
from security.encryption import (
    CryptographicManager, SecurityManager, SecureTransport,
    create_security_system, SecurityLevel, TrustLevel
)

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """System states"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"


class ComponentStatus(Enum):
    """Component status"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    endpoint: str
    version: str = "1.0"
    region: str = "default"
    tags: List[str] = field(default_factory=list)
    security_level: SecurityLevel = SecurityLevel.STANDARD
    trust_level: TrustLevel = TrustLevel.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemComponent:
    """System component wrapper"""
    component_id: str
    component_type: str
    status: ComponentStatus = ComponentStatus.STOPPED
    last_health_check: Optional[datetime] = None
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentCommunicationSystem:
    """Main agent communication system integrating all components"""
    
    def __init__(self, system_id: str, config: Optional[Dict[str, Any]] = None):
        self.system_id = system_id
        self.config = config or {}
        
        # System state
        self.state = SystemState.INITIALIZING
        self.start_time: Optional[datetime] = None
        
        # Core components
        self.message_router: Optional[MessageRouter] = None
        self.agent_registry: Optional[AgentRegistry] = None
        self.discovery_service: Optional[AgentDiscoveryService] = None
        self.message_persistor: Optional[MessagePersistor] = None
        self.event_bus: Optional[EventBus] = None
        self.coordination_engine: Optional[CoordinationEngine] = None
        self.workflow_engine: Optional[WorkflowEngine] = None
        self.metric_collector: Optional[MetricCollector] = None
        self.alert_manager: Optional[AlertManager] = None
        self.flow_analyzer: Optional[MessageFlowAnalyzer] = None
        self.monitoring_dashboard: Optional[MonitoringDashboard] = None
        self.crypto_manager: Optional[CryptographicManager] = None
        self.security_manager: Optional[SecurityManager] = None
        self.secure_transport: Optional[SecureTransport] = None
        
        # Component management
        self.components: Dict[str, SystemComponent] = {}
        self.component_dependencies: Dict[str, List[str]] = {}
        
        # Agent management
        self.registered_agents: Dict[str, AgentConfig] = {}
        self.agent_connections: Dict[str, Dict[str, Any]] = {}
        
        # Protocol orchestration
        self.protocol_orchestrator: Optional[ProtocolOrchestrator] = None
        
        # Message queues and processing
        self.incoming_queue: asyncio.Queue = asyncio.Queue()
        self.outgoing_queue: asyncio.Queue = asyncio.Queue()
        self.message_handlers: Dict[str, Callable] = {}
        
        # Processing tasks
        self.processing_tasks: List[asyncio.Task] = []
        self.running = False
        
        # Thread safety
        self.system_lock = threading.RLock()
        
        # Statistics and metrics
        self.system_stats = {
            'messages_processed': 0,
            'messages_failed': 0,
            'agents_registered': 0,
            'coordination_tasks': 0,
            'security_violations': 0,
            'uptime_seconds': 0
        }
        
        logger.info(f"Agent communication system {system_id} initialized")
    
    async def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            with self.system_lock:
                logger.info("Starting agent communication system initialization...")
                
                # Initialize components in dependency order
                await self._initialize_core_components()
                await self._initialize_monitoring_components()
                await self._initialize_security_components()
                await self._initialize_event_components()
                await self._initialize_protocols()
                
                # Set up message processing
                await self._setup_message_processing()
                
                # Set up event handlers
                await self._setup_event_handlers()
                
                # Mark system as running
                self.state = SystemState.RUNNING
                self.start_time = datetime.now()
                
                logger.info(f"Agent communication system {self.system_id} initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            self.state = SystemState.ERROR
            return False
    
    async def start(self):
        """Start the agent communication system"""
        if self.state != SystemState.RUNNING:
            if not await self.initialize():
                raise RuntimeError("System initialization failed")
        
        self.running = True
        
        # Start all components
        await self._start_all_components()
        
        # Start processing tasks
        await self._start_processing_tasks()
        
        logger.info(f"Agent communication system {self.system_id} started")
    
    async def stop(self):
        """Stop the agent communication system"""
        logger.info(f"Stopping agent communication system {self.system_id}...")
        
        self.state = SystemState.SHUTTING_DOWN
        self.running = False
        
        try:
            # Stop processing tasks
            await self._stop_processing_tasks()
            
            # Stop all components
            await self._stop_all_components()
            
            # Update final statistics
            if self.start_time:
                self.system_stats['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
            
            self.state = SystemState.STOPPED
            logger.info(f"Agent communication system {self.system_id} stopped")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")
            self.state = SystemState.ERROR
    
    async def register_agent(self, agent_config: AgentConfig) -> bool:
        """Register an agent in the system"""
        try:
            with self.system_lock:
                # Validate agent configuration
                if not agent_config.agent_id or not agent_config.agent_type:
                    logger.error("Agent registration failed: missing required fields")
                    return False
                
                # Create agent info for registry
                agent_info = AgentInfo(
                    agent_id=agent_config.agent_id,
                    agent_type=agent_config.agent_type,
                    capabilities=agent_config.capabilities,
                    endpoint=agent_config.endpoint,
                    version=agent_config.version,
                    metadata={
                        'region': agent_config.region,
                        'tags': agent_config.tags,
                        'security_level': agent_config.security_level.value,
                        'trust_level': agent_config.trust_level.value,
                        **agent_config.metadata
                    }
                )
                
                # Register in discovery service
                success = self.agent_registry.register_agent(agent_info)
                
                if success:
                    # Store agent configuration
                    self.registered_agents[agent_config.agent_id] = agent_config
                    
                    # Set trust level in security manager
                    self.security_manager.set_trust_level(agent_config.agent_id, agent_config.trust_level)
                    
                    # Update statistics
                    self.system_stats['agents_registered'] += 1
                    
                    # Publish agent registered event
                    await self.event_bus.publish_event(Event(
                        event_id=str(uuid.uuid4()),
                        event_type=EventType.AGENT_REGISTERED,
                        source=self.system_id,
                        timestamp=datetime.now(),
                        data={
                            'agent_id': agent_config.agent_id,
                            'agent_type': agent_config.agent_type,
                            'capabilities': agent_config.capabilities
                        }
                    ))
                    
                    logger.info(f"Agent {agent_config.agent_id} registered successfully")
                    return True
                else:
                    logger.error(f"Failed to register agent {agent_config.agent_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error registering agent {agent_config.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the system"""
        try:
            with self.system_lock:
                if agent_id not in self.registered_agents:
                    logger.warning(f"Agent {agent_id} not found for unregistration")
                    return False
                
                # Unregister from discovery service
                success = self.agent_registry.unregister_agent(agent_id)
                
                if success:
                    # Remove from registered agents
                    del self.registered_agents[agent_id]
                    
                    # Update statistics
                    self.system_stats['agents_registered'] -= 1
                    
                    # Publish agent unregistered event
                    await self.event_bus.publish_event(Event(
                        event_id=str(uuid.uuid4()),
                        event_type=EventType.AGENT_UNREGISTERED,
                        source=self.system_id,
                        timestamp=datetime.now(),
                        data={'agent_id': agent_id}
                    ))
                    
                    logger.info(f"Agent {agent_id} unregistered successfully")
                    return True
                else:
                    logger.error(f"Failed to unregister agent {agent_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}")
            return False
    
    async def send_message(self, message: BaseMessage, 
                          secure: bool = True) -> bool:
        """Send a message through the system"""
        try:
            if not self.running:
                logger.warning("System not running, message not sent")
                return False
            
            # Apply security if requested
            if secure:
                message = self.security_manager.encrypt_message(message)
            
            # Route message
            route_id = await self.message_router.route_message(message, self.secure_transport)
            
            # Track message flow
            self.flow_analyzer.track_message(message)
            
            # Update statistics
            self.system_stats['messages_processed'] += 1
            
            # Publish message sent event
            await self.event_bus.publish_event(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.MESSAGE_SENT,
                source=self.system_id,
                timestamp=datetime.now(),
                data={
                    'message_id': message.metadata.message_id,
                    'sender': message.sender_id,
                    'recipient': message.recipient_id,
                    'message_type': message.message_type.value,
                    'route_id': route_id
                }
            ))
            
            logger.debug(f"Message {message.metadata.message_id} sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.system_stats['messages_failed'] += 1
            return False
    
    async def discover_agents(self, criteria: Dict[str, Any]) -> List[AgentInfo]:
        """Discover agents matching criteria"""
        try:
            return self.agent_registry.discover_agents(criteria)
        except Exception as e:
            logger.error(f"Agent discovery failed: {e}")
            return []
    
    async def start_coordination(self, coordinator_id: str, task_type: str,
                               participants: List[str], parameters: Dict[str, Any]) -> str:
        """Start coordination among agents"""
        try:
            task_id = await self.coordination_engine.start_coordination(
                coordinator_id=coordinator_id,
                task_type=task_type,
                participants=participants,
                parameters=parameters
            )
            
            # Update statistics
            self.system_stats['coordination_tasks'] += 1
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to start coordination: {e}")
            raise
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            status = {
                'system_id': self.system_id,
                'state': self.state.value,
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'statistics': self.system_stats.copy(),
                'components': {},
                'registered_agents': len(self.registered_agents),
                'active_connections': len(self.agent_connections)
            }
            
            # Get component statuses
            for component_id, component in self.components.items():
                status['components'][component_id] = {
                    'status': component.status.value,
                    'last_health_check': component.last_health_check.isoformat() if component.last_health_check else None,
                    'error_count': component.error_count
                }
            
            # Get component-specific stats
            if self.message_router:
                status['router_stats'] = self.message_router.get_router_stats()
            
            if self.metric_collector:
                status['monitoring_stats'] = self.metric_collector.get_collector_stats()
            
            if self.alert_manager:
                status['alert_stats'] = self.alert_manager.get_alert_stats()
            
            if self.flow_analyzer:
                status['flow_stats'] = self.flow_analyzer.get_analyzer_stats()
            
            if self.agent_registry:
                status['registry_stats'] = self.agent_registry.get_registry_stats()
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                'system_id': self.system_id,
                'state': 'error',
                'error': str(e)
            }
    
    async def _initialize_core_components(self):
        """Initialize core components"""
        # Message router
        router_path = f"./storage/{self.system_id}/router"
        self.message_router = create_router_with_default_config(f"router_{self.system_id}")
        self._register_component("message_router", "router", self.message_router)
        
        # Message persistor
        persistor_path = f"./storage/{self.system_id}/persistence"
        self.message_persistor = create_default_persistor(f"persistor_{self.system_id}", persistor_path)
        self._register_component("message_persistor", "persistence", self.message_persistor)
        
        # Agent registry and discovery
        self.agent_registry, self.discovery_service = create_default_discovery_service(f"discovery_{self.system_id}")
        self._register_component("agent_registry", "discovery", self.agent_registry)
        self._register_component("discovery_service", "discovery", self.discovery_service)
    
    async def _initialize_monitoring_components(self):
        """Initialize monitoring components"""
        monitoring_path = f"./storage/{self.system_id}/monitoring"
        self.metric_collector, self.alert_manager, self.flow_analyzer, self.monitoring_dashboard = create_monitoring_system(
            f"monitoring_{self.system_id}", monitoring_path
        )
        
        self._register_component("metric_collector", "monitoring", self.metric_collector)
        self._register_component("alert_manager", "monitoring", self.alert_manager)
        self._register_component("flow_analyzer", "monitoring", self.flow_analyzer)
        self._register_component("monitoring_dashboard", "monitoring", self.monitoring_dashboard)
    
    async def _initialize_security_components(self):
        """Initialize security components"""
        self.crypto_manager, self.security_manager, self.secure_transport = create_security_system(f"security_{self.system_id}")
        self._register_component("crypto_manager", "security", self.crypto_manager)
        self._register_component("security_manager", "security", self.security_manager)
        self._register_component("secure_transport", "security", self.secure_transport)
    
    async def _initialize_event_components(self):
        """Initialize event and coordination components"""
        self.event_bus, self.coordination_engine, self.workflow_engine = await create_default_event_system(f"events_{self.system_id}")
        self._register_component("event_bus", "events", self.event_bus)
        self._register_component("coordination_engine", "coordination", self.coordination_engine)
        self._register_component("workflow_engine", "workflow", self.workflow_engine)
    
    async def _initialize_protocols(self):
        """Initialize protocol orchestrator"""
        self.protocol_orchestrator = ProtocolOrchestrator(f"orchestrator_{self.system_id}")
        
        # Add protocol instances
        self.protocol_orchestrator.add_protocol(CommunicationPattern.PUBLISH_SUBSCRIBE)
        self.protocol_orchestrator.add_protocol(CommunicationPattern.REQUEST_RESPONSE)
        self.protocol_orchestrator.add_protocol(CommunicationPattern.AGGREGATION)
        
        self._register_component("protocol_orchestrator", "protocols", self.protocol_orchestrator)
    
    async def _setup_message_processing(self):
        """Set up message processing pipelines"""
        # This would set up the actual message processing logic
        # For now, it's a placeholder for the integration
        pass
    
    async def _setup_event_handlers(self):
        """Set up default event handlers"""
        if self.event_bus:
            # Add system event handlers
            await self.event_bus.start()
            
            # Subscribe to system events
            await self.event_bus.subscribe(
                [EventType.SYSTEM_STARTED, EventType.SYSTEM_STOPPED],
                self._handle_system_events
            )
            
            # Subscribe to agent events
            await self.event_bus.subscribe(
                [EventType.AGENT_REGISTERED, EventType.AGENT_UNREGISTERED],
                self._handle_agent_events
            )
            
            # Subscribe to message events
            await self.event_bus.subscribe(
                [EventType.MESSAGE_SENT, EventType.MESSAGE_FAILED],
                self._handle_message_events
            )
    
    async def _start_all_components(self):
        """Start all registered components"""
        for component_id, component in self.components.items():
            try:
                component.status = ComponentStatus.STARTING
                
                if hasattr(component, 'start') and callable(component.start):
                    await component.start()
                
                component.status = ComponentStatus.RUNNING
                component.last_health_check = datetime.now()
                
                logger.info(f"Component {component_id} started")
                
            except Exception as e:
                component.status = ComponentStatus.ERROR
                component.error_count += 1
                logger.error(f"Failed to start component {component_id}: {e}")
    
    async def _stop_all_components(self):
        """Stop all registered components"""
        for component_id, component in list(self.components.items()):
            try:
                component.status = ComponentStatus.STOPPING
                
                if hasattr(component, 'stop') and callable(component.stop):
                    await component.stop()
                
                component.status = ComponentStatus.STOPPED
                logger.info(f"Component {component_id} stopped")
                
            except Exception as e:
                component.status = ComponentStatus.ERROR
                logger.error(f"Failed to stop component {component_id}: {e}")
    
    async def _start_processing_tasks(self):
        """Start background processing tasks"""
        # Message processing task
        self.processing_tasks.append(
            asyncio.create_task(self._message_processing_loop())
        )
        
        # Health monitoring task
        self.processing_tasks.append(
            asyncio.create_task(self._health_monitoring_loop())
        )
        
        # Cleanup task
        self.processing_tasks.append(
            asyncio.create_task(self._cleanup_loop())
        )
    
    async def _stop_processing_tasks(self):
        """Stop all processing tasks"""
        for task in self.processing_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        self.processing_tasks.clear()
    
    async def _message_processing_loop(self):
        """Background loop for message processing"""
        while self.running:
            try:
                # Process incoming messages
                try:
                    message = await asyncio.wait_for(self.incoming_queue.get(), timeout=1.0)
                    await self._process_message(message)
                except asyncio.TimeoutError:
                    pass
                
                # Process outgoing messages
                try:
                    message = await asyncio.wait_for(self.outgoing_queue.get(), timeout=0.1)
                    await self.send_message(message)
                except asyncio.TimeoutError:
                    pass
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _health_monitoring_loop(self):
        """Background loop for health monitoring"""
        while self.running:
            try:
                # Update component health
                for component_id, component in self.components.items():
                    component.last_health_check = datetime.now()
                    
                    # Check if component is still responsive
                    if hasattr(component, 'ping') and callable(component.ping):
                        try:
                            # Ping would be implemented in actual components
                            pass
                        except Exception:
                            component.status = ComponentStatus.ERROR
                            component.error_count += 1
                
                # Evaluate alerts
                if self.alert_manager and self.metric_collector:
                    self.alert_manager.evaluate_alerts(self.metric_collector)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """Background loop for cleanup operations"""
        while self.running:
            try:
                # Cleanup expired messages
                if self.message_persistor:
                    self.message_persistor.cleanup_expired_messages()
                
                # Update system metrics
                if self.metric_collector:
                    self.metric_collector.set_gauge('system_uptime', 
                                                   (datetime.now() - self.start_time).total_seconds())
                    self.metric_collector.set_gauge('registered_agents', len(self.registered_agents))
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def _process_message(self, message: BaseMessage):
        """Process a single message"""
        try:
            # Handle message based on type
            if message.message_type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(message)
            elif message.message_type == MessageType.DISCOVERY:
                response = await self.discovery_service.handle_discovery_request(message, self.secure_transport)
                if response:
                    await self.send_message(response)
            elif message.message_type == MessageType.AGENT_COORDINATION:
                await self._handle_coordination_request(message)
            
        except Exception as e:
            logger.error(f"Failed to process message {message.metadata.message_id}: {e}")
    
    async def _handle_heartbeat(self, message: BaseMessage):
        """Handle heartbeat message"""
        try:
            agent_id = message.sender_id
            health_data = message.payload.get('health_data', {})
            
            self.agent_registry.update_heartbeat(agent_id, health_data)
            
        except Exception as e:
            logger.error(f"Failed to handle heartbeat: {e}")
    
    async def _handle_coordination_request(self, message: BaseMessage):
        """Handle coordination request"""
        try:
            # This would handle coordination requests
            # For now, it's a placeholder
            pass
        except Exception as e:
            logger.error(f"Failed to handle coordination request: {e}")
    
    async def _handle_system_events(self, event: Event):
        """Handle system-level events"""
        logger.info(f"System event: {event.event_type.value} - {event.description}")
    
    async def _handle_agent_events(self, event: Event):
        """Handle agent-related events"""
        logger.info(f"Agent event: {event.event_type.value} - Agent {event.data.get('agent_id')}")
    
    async def _handle_message_events(self, event: Event):
        """Handle message-related events"""
        logger.debug(f"Message event: {event.event_type.value} - {event.data.get('message_id')}")
    
    def _register_component(self, component_id: str, component_type: str, component: Any):
        """Register a system component"""
        system_component = SystemComponent(
            component_id=component_id,
            component_type=component_type
        )
        
        self.components[component_id] = system_component
        
        logger.info(f"Registered component: {component_id} ({component_type})")


# Factory function and example usage
async def create_communication_system(system_id: str = "default", 
                                    config: Optional[Dict[str, Any]] = None) -> AgentCommunicationSystem:
    """Create and initialize a complete agent communication system"""
    system = AgentCommunicationSystem(system_id, config)
    await system.initialize()
    return system


async def create_agent_communication_system_example():
    """Example of creating and using the agent communication system"""
    
    # Create system
    system = await create_communication_system("example_system")
    
    # Register agents
    agent_configs = [
        AgentConfig(
            agent_id="trading_agent_1",
            agent_type="trading",
            capabilities=["signal_generation", "risk_management"],
            endpoint="tcp://localhost:8001",
            region="us-east-1",
            tags=["crypto", "high_frequency"]
        ),
        AgentConfig(
            agent_id="analysis_agent_1", 
            agent_type="analysis",
            capabilities=["pattern_recognition", "prediction"],
            endpoint="tcp://localhost:8002",
            region="us-east-1",
            tags=["ml", "technical_analysis"]
        )
    ]
    
    for config in agent_configs:
        await system.register_agent(config)
    
    # Send test messages
    trade_signal = MessageFactory.create_trade_signal(
        sender_id="trading_agent_1",
        symbol="BTCUSDT",
        signal="BUY",
        price=45000.0,
        confidence=0.85
    )
    
    await system.send_message(trade_signal)
    
    # Start coordination
    await system.start_coordination(
        coordinator_id="coordinator_1",
        task_type="market_analysis",
        participants=["analysis_agent_1"],
        parameters={"symbol": "BTCUSDT", "timeframe": "1h"}
    )
    
    # Get system status
    status = await system.get_system_status()
    print(f"System status: {json.dumps(status, indent=2, default=str)}")
    
    # Keep system running for a bit
    await asyncio.sleep(10)
    
    # Stop system
    await system.stop()


if __name__ == "__main__":
    # Example usage
    asyncio.run(create_agent_communication_system_example())