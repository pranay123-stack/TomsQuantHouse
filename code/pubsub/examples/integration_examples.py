"""
Main System Orchestrator and Integration Examples
Coordinates all components of the Redis pub/sub system for agent coordination
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import signal
import sys

from core.redis_client import RedisPubSubClient, MessagePriority, AgentType
from core.message_router import MessageRouter, create_default_router
from core.message_persistence import MessagePersistence, create_persistence_service, MessageRetention
from core.event_orchestrator import EventBus, WorkflowOrchestrator, create_event_driven_system
from core.message_orchestrator import MessageOrchestrator
from agents.agent_discovery import AgentRegistry, AgentDiscoveryService, create_default_discovery_service
from monitoring.monitoring_system import MetricsCollector, AlertManager, AnalyticsEngine, create_monitoring_system
from security.security_manager import SecurityManager, SecurityMiddleware, create_secure_system
from protocols.message_schemas import (
    ProtocolMessage, MessageType, MessageStatus, AgentMetadata, TradeSignal, Prediction, Alert,
    MessageFactory, asdict
)


class SystemStatus(Enum):
    """System status states"""
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SystemConfig:
    """System configuration"""
    redis_config: Dict[str, Any]
    system_id: str = "pubsub_system_001"
    log_level: str = "INFO"
    auto_start: bool = True
    health_check_interval: int = 30
    components_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System-wide metrics"""
    uptime_seconds: float
    total_messages_processed: int
    active_agents: int
    system_health: str
    component_status: Dict[str, str]
    last_health_check: datetime


class PubSubSystemOrchestrator:
    """Main orchestrator for the Redis pub/sub system"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.system_id = config.system_id
        
        # System status
        self.status = SystemStatus.INITIALIZING
        self.start_time: Optional[datetime] = None
        self.components: Dict[str, Any] = {}
        self.component_status: Dict[str, str] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {
            'system_start': [],
            'system_stop': [],
            'system_error': [],
            'agent_registered': [],
            'agent_unregistered': [],
            'message_processed': [],
            'alert_triggered': []
        }
        
        # System statistics
        self.stats = {
            'startup_time': 0.0,
            'messages_processed': 0,
            'agents_registered': 0,
            'errors_encountered': 0,
            'restarts': 0
        }
        
        # Background tasks
        self.background_tasks: List[asyncio.Task] = []
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    async def initialize(self):
        """Initialize all system components"""
        try:
            self.logger.info(f"Initializing pub/sub system {self.system_id}")
            self.status = SystemStatus.INITIALIZING
            
            # Initialize core Redis client
            redis_client = RedisPubSubClient(**self.config.redis_config)
            await redis_client.connect()
            self.components['redis_client'] = redis_client
            
            # Initialize agent discovery
            registry, discovery_service, health_monitor = await create_default_discovery_service(
                self.config.redis_config
            )
            self.components['agent_registry'] = registry
            self.components['discovery_service'] = discovery_service
            self.components['health_monitor'] = health_monitor
            
            # Initialize message router
            message_router = await create_default_router(self.config.redis_config)
            self.components['message_router'] = message_router
            
            # Initialize message persistence
            message_persistence = await create_persistence_service(
                self.config.redis_config,
                storage_backend=self.components_config.get('storage_backend', 'redis_with_sqlite'),
                storage_path=self.components_config.get('storage_path', './pubsub_storage')
            )
            self.components['message_persistence'] = message_persistence
            
            # Initialize monitoring system
            monitoring_system = await create_monitoring_system(self.config.redis_config)
            self.components['monitoring'] = monitoring_system
            
            # Initialize security system
            security_system = await create_secure_system(self.config.redis_config)
            self.components['security'] = security_system
            
            # Initialize event-driven system
            event_system = await create_event_driven_system(self.config.redis_config)
            self.components['event_bus'] = event_system['event_bus']
            self.components['workflow_orchestrator'] = event_system['workflow_orchestrator']
            
            # Initialize message orchestrator for coordinating flows
            message_orchestrator = MessageOrchestrator(
                redis_client, message_router, message_persistence, self.components['event_bus']
            )
            self.components['message_orchestrator'] = message_orchestrator
            
            # Update component status
            for component_name in self.components.keys():
                self.component_status[component_name] = 'initialized'
            
            self.logger.info("System initialization completed")
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            self.status = SystemStatus.ERROR
            raise
    
    async def start(self):
        """Start all system components"""
        try:
            self.logger.info(f"Starting pub/sub system {self.system_id}")
            self.status = SystemStatus.STARTING
            
            startup_start = datetime.utcnow()
            
            # Start all components
            for component_name, component in self.components.items():
                try:
                    if hasattr(component, 'start'):
                        await component.start()
                    elif hasattr(component, 'connect'):
                        await component.connect()
                    
                    self.component_status[component_name] = 'running'
                    self.logger.info(f"Component {component_name} started")
                    
                except Exception as e:
                    self.logger.error(f"Failed to start component {component_name}: {e}")
                    self.component_status[component_name] = 'error'
                    raise
            
            # Start system monitoring
            self.background_tasks.append(asyncio.create_task(self._system_monitor_loop()))
            self.background_tasks.append(asyncio.create_task(self._health_check_loop()))
            self.background_tasks.append(asyncio.create_task(self._metrics_collection_loop()))
            
            # Record startup time
            startup_time = (datetime.utcnow() - startup_start).total_seconds()
            self.stats['startup_time'] = startup_time
            self.start_time = datetime.utcnow()
            
            self.status = SystemStatus.RUNNING
            
            # Trigger startup events
            await self._trigger_event('system_start', {
                'system_id': self.system_id,
                'startup_time': startup_time,
                'components_started': len(self.components)
            })
            
            self.logger.info(f"System started successfully in {startup_time:.2f} seconds")
            
        except Exception as e:
            self.logger.error(f"System startup failed: {e}")
            self.status = SystemStatus.ERROR
            raise
    
    async def stop(self):
        """Stop all system components gracefully"""
        try:
            self.logger.info(f"Stopping pub/sub system {self.system_id}")
            self.status = SystemStatus.STOPPING
            
            # Stop background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Stop all components in reverse order
            component_names = list(self.components.keys())
            component_names.reverse()
            
            for component_name in component_names:
                try:
                    component = self.components[component_name]
                    
                    if hasattr(component, 'stop'):
                        await component.stop()
                    elif hasattr(component, 'disconnect'):
                        await component.disconnect()
                    
                    self.component_status[component_name] = 'stopped'
                    self.logger.info(f"Component {component_name} stopped")
                    
                except Exception as e:
                    self.logger.error(f"Failed to stop component {component_name}: {e}")
            
            # Trigger shutdown events
            await self._trigger_event('system_stop', {
                'system_id': self.system_id,
                'uptime_seconds': self.get_uptime(),
                'total_messages': self.stats['messages_processed']
            })
            
            self.status = SystemStatus.STOPPED
            self.logger.info("System stopped successfully")
            
        except Exception as e:
            self.logger.error(f"System shutdown failed: {e}")
            self.status = SystemStatus.ERROR
    
    async def restart(self):
        """Restart the system"""
        try:
            self.logger.info("Restarting system")
            self.stats['restarts'] += 1
            
            await self.stop()
            await asyncio.sleep(5)  # Brief pause before restart
            
            # Reinitialize components
            self.components.clear()
            self.component_status.clear()
            self.background_tasks.clear()
            
            await self.initialize()
            await self.start()
            
            self.logger.info("System restart completed")
            
        except Exception as e:
            self.logger.error(f"System restart failed: {e}")
            self.status = SystemStatus.ERROR
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
        else:
            self.event_handlers[event_type] = [handler]
    
    async def register_agent(self, agent_metadata: AgentMetadata) -> bool:
        """Register an agent in the system"""
        try:
            registry = self.components['agent_registry']
            success = await registry.register_agent(agent_metadata)
            
            if success:
                self.stats['agents_registered'] += 1
                
                # Trigger agent registered event
                await self._trigger_event('agent_registered', {
                    'agent_id': agent_metadata.agent_id,
                    'agent_type': agent_metadata.agent_type
                })
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_metadata.agent_id}: {e}")
            return False
    
    async def process_message(self, message: ProtocolMessage) -> bool:
        """Process a message through the system"""
        try:
            # Security check
            security_system = self.components['security']
            middleware = security_system['security_middleware']
            
            # Process with security middleware
            encrypted_message = await middleware.process_outgoing_message(message)
            
            # Route message
            message_router = self.components['message_router']
            await message_router.route_message(message)
            
            # Persist message if required
            if message.requires_acknowledgment:
                message_persistence = self.components['message_persistence']
                await message_persistence.store_message(message)
            
            # Update statistics
            self.stats['messages_processed'] += 1
            
            # Trigger message processed event
            await self._trigger_event('message_processed', {
                'message_id': message.message_id,
                'message_type': message.message_type.value,
                'channel': message.channel
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process message {message.message_id}: {e}")
            self.stats['errors_encountered'] += 1
            return False
    
    async def get_system_status(self) -> SystemMetrics:
        """Get current system status and metrics"""
        uptime_seconds = self.get_uptime()
        
        # Get component health
        component_health = {}
        for component_name, status in self.component_status.items():
            component_health[component_name] = status
        
        # Get active agents count
        registry = self.components.get('agent_registry')
        active_agents = 0
        if registry:
            stats = registry.get_registry_stats()
            active_agents = stats.get('active_agents', 0)
        
        # Determine overall system health
        system_health = self._calculate_system_health(component_health)
        
        return SystemMetrics(
            uptime_seconds=uptime_seconds,
            total_messages_processed=self.stats['messages_processed'],
            active_agents=active_agents,
            system_health=system_health,
            component_status=component_health,
            last_health_check=datetime.utcnow()
        )
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        if self.start_time:
            return (datetime.utcnow() - self.start_time).total_seconds()
        return 0.0
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            'system_id': self.system_id,
            'status': self.status.value,
            'uptime_seconds': self.get_uptime(),
            'statistics': self.stats.copy(),
            'component_status': self.component_status.copy(),
            'registered_event_handlers': {
                event_type: len(handlers) 
                for event_type, handlers in self.event_handlers.items()
            }
        }
    
    async def _system_monitor_loop(self):
        """Monitor system health and performance"""
        while True:
            try:
                # Check system health
                metrics = await self.get_system_status()
                
                # Check for degraded performance
                if metrics.system_health == 'degraded':
                    self.logger.warning("System health degraded")
                    # Could trigger automatic remediation here
                
                # Monitor critical thresholds
                if metrics.active_agents == 0:
                    self.logger.warning("No active agents registered")
                
                if self.stats['errors_encountered'] > 100:
                    self.logger.error("High error rate detected")
                    # Could trigger alerts or restart
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _health_check_loop(self):
        """Periodic health checks"""
        while True:
            try:
                # Check Redis connectivity
                redis_client = self.components.get('redis_client')
                if redis_client and not redis_client.is_connected:
                    self.logger.error("Redis connection lost")
                    self.status = SystemStatus.DEGRADED
                    
                    # Attempt reconnection
                    try:
                        await redis_client.connect()
                        self.logger.info("Redis reconnection successful")
                        if self.status == SystemStatus.DEGRADED:
                            self.status = SystemStatus.RUNNING
                    except Exception as e:
                        self.logger.error(f"Redis reconnection failed: {e}")
                
                # Check component health
                for component_name, component in self.components.items():
                    if hasattr(component, 'get_health_status'):
                        health_status = await component.get_health_status()
                        if health_status != 'healthy':
                            self.logger.warning(f"Component {component_name} health: {health_status}")
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(30)
    
    async def _metrics_collection_loop(self):
        """Collect system metrics"""
        while True:
            try:
                # Collect metrics from components
                if 'monitoring' in self.components:
                    monitoring = self.components['monitoring']
                    
                    # Record message events
                    metrics_collector = monitoring['metrics_collector']
                    await metrics_collector.record_message_event('sent')
                    
                    # Collect latency if available
                    # This would be enhanced with actual latency measurements
                
                await asyncio.sleep(10)  # Collect every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)
    
    def _calculate_system_health(self, component_status: Dict[str, str]) -> str:
        """Calculate overall system health"""
        error_components = [name for name, status in component_status.items() if status == 'error']
        
        if not component_status:
            return 'unknown'
        
        error_rate = len(error_components) / len(component_status)
        
        if error_rate == 0:
            return 'healthy'
        elif error_rate <= 0.3:
            return 'degraded'
        else:
            return 'critical'
    
    async def _trigger_event(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger system events"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)
                except Exception as e:
                    self.logger.error(f"Event handler error for {event_type}: {e}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'pubsub_system_{self.system_id}.log')
            ]
        )
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        
        # Create task for graceful shutdown
        asyncio.create_task(self.stop())
        sys.exit(0)


class MessageOrchestrator:
    """Orchestrates message flows between components"""
    
    def __init__(self, redis_client: RedisPubSubClient, message_router: MessageRouter,
                 message_persistence: MessagePersistence, event_bus: EventBus):
        self.redis = redis_client
        self.message_router = message_router
        self.message_persistence = message_persistence
        self.event_bus = event_bus
        
        self.logger = logging.getLogger(__name__)
    
    async def orchestrate_trade_signal_flow(self, trade_signal: TradeSignal, 
                                          sender_id: str) -> str:
        """Orchestrate a complete trade signal flow"""
        try:
            # Create trade signal message
            message = MessageFactory.create_trade_signal(sender_id, trade_signal)
            
            # Discover suitable trading agents
            # This would use the agent registry to find appropriate agents
            
            # Process the message
            await self.process_message(message)
            
            # Trigger workflow for trade execution
            workflow_id = await self._create_trade_execution_workflow(message)
            
            self.logger.info(f"Trade signal flow orchestrated: {message.message_id}")
            return message.message_id
            
        except Exception as e:
            self.logger.error(f"Trade signal flow orchestration failed: {e}")
            raise
    
    async def orchestrate_prediction_flow(self, prediction: Prediction, 
                                        sender_id: str) -> str:
        """Orchestrate a prediction flow"""
        try:
            # Create prediction message
            message = MessageFactory.create_prediction(sender_id, prediction)
            
            # Process the message
            await self.process_message(message)
            
            # Notify relevant agents about new prediction
            await self._notify_prediction_consumers(message)
            
            self.logger.info(f"Prediction flow orchestrated: {message.message_id}")
            return message.message_id
            
        except Exception as e:
            self.logger.error(f"Prediction flow orchestration failed: {e}")
            raise
    
    async def process_message(self, message: ProtocolMessage):
        """Process message through the orchestrator"""
        try:
            # Route message
            await self.message_router.route_message(message)
            
            # Persist if required
            if message.requires_acknowledgment:
                await self.message_persistence.store_message(message)
            
            # Publish event
            from core.event_orchestrator import Event, EventType
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.MESSAGE_SENT,
                source="message_orchestrator",
                data={'message_id': message.message_id, 'message_type': message.message_type.value},
                correlation_id=message.message_id
            )
            await self.event_bus.publish_event(event)
            
        except Exception as e:
            self.logger.error(f"Message orchestration failed: {e}")
            raise
    
    async def _create_trade_execution_workflow(self, message: ProtocolMessage) -> str:
        """Create a workflow for trade execution"""
        # This would integrate with the workflow orchestrator
        # For now, return a placeholder
        return f"workflow_{message.message_id}"
    
    async def _notify_prediction_consumers(self, message: ProtocolMessage):
        """Notify agents that consume predictions"""
        # This would discover and notify agents interested in predictions
        pass


# Integration examples and demonstrations
async def run_basic_integration_example():
    """Run a basic integration example"""
    # System configuration
    config = SystemConfig(
        redis_config={
            'host': 'localhost',
            'port': 6379,
            'db': 0
        },
        system_id='example_system'
    )
    
    # Create and start system
    orchestrator = PubSubSystemOrchestrator(config)
    await orchestrator.initialize()
    await orchestrator.start()
    
    try:
        # Register example agents
        trader_agent = AgentMetadata(
            agent_id='trader_001',
            agent_type='trader',
            name='Main Trading Agent',
            version='1.0.0',
            capabilities=['trade_execution', 'risk_management'],
            supported_symbols=['AAPL', 'GOOGL', 'MSFT']
        )
        
        await orchestrator.register_agent(trader_agent)
        
        # Create and process example messages
        trade_signal = TradeSignal(
            symbol='AAPL',
            action='BUY',
            quantity=100,
            price=150.0,
            confidence=0.85
        )
        
        message = MessageFactory.create_trade_signal('trader_001', trade_signal)
        await orchestrator.process_message(message)
        
        # Wait a bit for processing
        await asyncio.sleep(5)
        
        # Get system status
        status = await orchestrator.get_system_status()
        print(f"System Status: {status.system_health}")
        print(f"Messages Processed: {status.total_messages_processed}")
        print(f"Active Agents: {status.active_agents}")
        print(f"Uptime: {status.uptime_seconds:.2f} seconds")
        
    finally:
        await orchestrator.stop()


async def run_comprehensive_example():
    """Run a comprehensive system example"""
    # System configuration with all components
    config = SystemConfig(
        redis_config={
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None  # Add password if needed
        },
        system_id='comprehensive_system',
        log_level='INFO',
        components_config={
            'storage_backend': 'redis_with_sqlite',
            'storage_path': './comprehensive_storage'
        }
    )
    
    orchestrator = PubSubSystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        await orchestrator.start()
        
        # Register multiple agents
        agents = [
            AgentMetadata(
                agent_id='trader_001',
                agent_type='trader',
                name='Alpha Trader',
                version='2.1.0',
                capabilities=['high_frequency_trading', 'arbitrage'],
                supported_symbols=['AAPL', 'GOOGL', 'TSLA', 'MSFT']
            ),
            AgentMetadata(
                agent_id='predictor_001',
                agent_type='predictor',
                name='ML Prediction Engine',
                version='1.5.2',
                capabilities=['price_prediction', 'volatility_forecasting'],
                supported_symbols=['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'AMZN']
            ),
            AgentMetadata(
                agent_id='alert_001',
                agent_type='alert_handler',
                name='Alert Manager',
                version='1.0.0',
                capabilities=['price_alerts', 'system_alerts'],
                supported_symbols=[]
            )
        ]
        
        for agent in agents:
            await orchestrator.register_agent(agent)
        
        # Process various message types
        trade_signals = [
            TradeSignal(symbol='AAPL', action='BUY', quantity=100, price=150.0, confidence=0.9),
            TradeSignal(symbol='GOOGL', action='SELL', quantity=50, price=2800.0, confidence=0.85),
            TradeSignal(symbol='TSLA', action='BUY', quantity=20, price=800.0, confidence=0.7)
        ]
        
        predictions = [
            Prediction(
                symbol='AAPL',
                predicted_direction='UP',
                predicted_price=155.0,
                timeframe='1d',
                confidence=0.8,
                model_version='v2.1'
            ),
            Prediction(
                symbol='GOOGL',
                predicted_direction='DOWN',
                predicted_price=2750.0,
                timeframe='4h',
                confidence=0.75,
                model_version='v2.1'
            )
        ]
        
        alerts = [
            Alert(
                alert_type='PRICE_THRESHOLD',
                severity='HIGH',
                title='AAPL Price Alert',
                message='AAPL reached target price',
                symbol='AAPL',
                threshold=150.0,
                current_value=151.5
            )
        ]
        
        # Process trade signals
        for trade_signal in trade_signals:
            message = MessageFactory.create_trade_signal('trader_001', trade_signal)
            await orchestrator.process_message(message)
            await asyncio.sleep(1)
        
        # Process predictions
        for prediction in predictions:
            message = MessageFactory.create_prediction('predictor_001', prediction)
            await orchestrator.process_message(message)
            await asyncio.sleep(1)
        
        # Process alerts
        for alert in alerts:
            message = MessageFactory.create_alert('alert_001', alert)
            await orchestrator.process_message(message)
            await asyncio.sleep(1)
        
        # Wait for processing
        await asyncio.sleep(10)
        
        # Generate comprehensive report
        system_stats = orchestrator.get_system_stats()
        system_status = await orchestrator.get_system_status()
        
        print("\n=== Comprehensive System Report ===")
        print(f"System ID: {system_stats['system_id']}")
        print(f"Status: {system_stats['status']}")
        print(f"Uptime: {system_status.uptime_seconds:.2f} seconds")
        print(f"Messages Processed: {system_status.total_messages_processed}")
        print(f"Active Agents: {system_status.active_agents}")
        print(f"System Health: {system_status.system_health}")
        
        print("\nComponent Status:")
        for component, status in system_status.component_status.items():
            print(f"  {component}: {status}")
        
        print("\nStatistics:")
        for key, value in system_stats['statistics'].items():
            print(f"  {key}: {value}")
        
        # Keep system running for a bit
        print("\nSystem running... Press Ctrl+C to stop")
        await asyncio.sleep(30)
        
    finally:
        print("\nShutting down system...")
        await orchestrator.stop()
        print("System shutdown complete")


async def main():
    """Main function to run examples"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Redis Pub/Sub System Examples')
    parser.add_argument('--example', choices=['basic', 'comprehensive'], 
                       default='basic', help='Example to run')
    
    args = parser.parse_args()
    
    if args.example == 'basic':
        await run_basic_integration_example()
    else:
        await run_comprehensive_example()


if __name__ == "__main__":
    asyncio.run(main())