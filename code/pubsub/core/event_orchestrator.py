"""
Event-Driven Architecture for Seamless Agent Coordination
Provides event handling, coordination, and orchestration for the pub/sub system
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any, Type, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import uuid
import hashlib
import logging
import weakref
import inspect
from abc import ABC, abstractmethod

from core.redis_client import RedisPubSubClient, MessagePriority
from core.message_router import MessageRouter
from core.message_persistence import MessagePersistence, MessageRetention
from protocols.message_schemas import ProtocolMessage, MessageType, MessageStatus


class EventType(Enum):
    """Event types for agent coordination"""
    # System events
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    
    # Message events
    MESSAGE_SENT = "message_sent"
    MESSAGE_DELIVERED = "message_delivered"
    MESSAGE_FAILED = "message_failed"
    MESSAGE_REPLAYED = "message_replayed"
    
    # Trading events
    TRADE_SIGNAL_CREATED = "trade_signal_created"
    TRADE_SIGNAL_EXECUTED = "trade_signal_executed"
    TRADE_SIGNAL_FAILED = "trade_signal_failed"
    PREDICTION_CREATED = "prediction_created"
    ALERT_TRIGGERED = "alert_triggered"
    
    # Coordination events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"


class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class WorkflowStatus(Enum):
    """Workflow status states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Event:
    """Event representation"""
    event_id: str
    event_type: EventType
    source: str  # Event source (agent ID, system component, etc.)
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    acknowledged: bool = False


@dataclass
class EventHandler:
    """Event handler configuration"""
    handler_id: str
    event_types: Set[EventType]
    handler_func: Callable
    priority: EventPriority = EventPriority.NORMAL
    timeout: int = 30
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    filter_func: Optional[Callable[[Event], bool]] = None


@dataclass
class Workflow:
    """Workflow definition for agent coordination"""
    workflow_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]  # Workflow steps configuration
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    retry_count: int = 0


@dataclass
class WorkflowStep:
    """Individual workflow step"""
    step_id: str
    name: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Step IDs this step depends on
    timeout: int = 60
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class EventBus:
    """Central event bus for publishing and subscribing to events"""
    
    def __init__(self, redis_client: RedisPubSubClient):
        self.redis = redis_client
        
        # Event handlers
        self.event_handlers: Dict[str, EventHandler] = {}
        self.event_queues: Dict[EventType, deque] = {
            event_type: deque() for event_type in EventType
        }
        
        # Event statistics
        self.event_stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handler_exceptions': 0,
            'average_processing_time': 0.0
        }
        
        # Processing tasks
        self.processing_tasks: Dict[EventType, asyncio.Task] = {}
        
        # Thread safety
        self.event_lock = asyncio.Lock()
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the event bus"""
        # Start event processing tasks for each event type
        for event_type in EventType:
            task = asyncio.create_task(self._process_event_queue(event_type))
            self.processing_tasks[event_type] = task
        
        self.logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus"""
        # Cancel processing tasks
        for task in self.processing_tasks.values():
            task.cancel()
        
        self.logger.info("Event bus stopped")
    
    async def publish_event(self, event: Event) -> bool:
        """Publish an event to the event bus"""
        try:
            async with self.event_lock:
                # Add to appropriate queue
                self.event_queues[event.event_type].append(event)
                
                # Publish to Redis for persistence and other subscribers
                event_message = ProtocolMessage(
                    message_id=f"event_{event.event_id}",
                    sender_id="event_bus",
                    channel="events",
                    message_type=MessageType.NOTIFICATION,
                    title=f"Event: {event.event_type.value}",
                    content=json.dumps({
                        'event_id': event.event_id,
                        'event_type': event.event_type.value,
                        'source': event.source,
                        'data': event.data,
                        'timestamp': event.timestamp.isoformat(),
                        'priority': event.priority.value
                    }),
                    priority=MessagePriority.NORMAL if event.priority == EventPriority.NORMAL else MessagePriority.HIGH
                )
                
                await self.redis.publish(event_message)
                
                # Update statistics
                self.event_stats['events_published'] += 1
                
                self.logger.debug(f"Event {event.event_id} ({event.event_type.value}) published")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to publish event {event.event_id}: {e}")
            return False
    
    async def subscribe_to_events(self, event_types: List[EventType], 
                                handler_func: Callable,
                                handler_id: str = None,
                                priority: EventPriority = EventPriority.NORMAL,
                                timeout: int = 30,
                                filter_func: Callable[[Event], bool] = None) -> str:
        """Subscribe to specific event types"""
        try:
            if not handler_id:
                handler_id = f"handler_{uuid.uuid4().hex[:8]}"
            
            handler = EventHandler(
                handler_id=handler_id,
                event_types=set(event_types),
                handler_func=handler_func,
                priority=priority,
                timeout=timeout,
                filter_func=filter_func
            )
            
            self.event_handlers[handler_id] = handler
            
            self.logger.info(f"Event handler {handler_id} subscribed to {len(event_types)} event types")
            return handler_id
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to events: {e}")
            raise
    
    async def unsubscribe_from_events(self, handler_id: str) -> bool:
        """Unsubscribe from events"""
        try:
            if handler_id in self.event_handlers:
                del self.event_handlers[handler_id]
                self.logger.info(f"Event handler {handler_id} unsubscribed")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe handler {handler_id}: {e}")
            return False
    
    async def handle_event(self, event: Event):
        """Handle an event"""
        try:
            # Find matching handlers
            matching_handlers = [
                handler for handler in self.event_handlers.values()
                if event.event_type in handler.event_types and handler.enabled
            ]
            
            # Sort by priority (highest first)
            matching_handlers.sort(key=lambda h: h.priority.value, reverse=True)
            
            # Execute handlers
            for handler in matching_handlers:
                try:
                    # Apply filter if specified
                    if handler.filter_func and not handler.filter_func(event):
                        continue
                    
                    # Execute handler with timeout
                    await asyncio.wait_for(
                        handler.handler_func(event),
                        timeout=handler.timeout
                    )
                    
                except asyncio.TimeoutError:
                    self.logger.warning(f"Handler {handler.handler_id} timed out for event {event.event_id}")
                except Exception as e:
                    self.logger.error(f"Handler {handler.handler_id} failed for event {event.event_id}: {e}")
                    self.event_stats['handler_exceptions'] += 1
            
            # Update statistics
            self.event_stats['events_processed'] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to handle event {event.event_id}: {e}")
            self.event_stats['events_failed'] += 1
    
    async def _process_event_queue(self, event_type: EventType):
        """Process events from a specific queue"""
        while True:
            try:
                if self.event_queues[event_type]:
                    event = self.event_queues[event_type].popleft()
                    
                    # Mark event as processing start time
                    start_time = datetime.utcnow()
                    
                    # Handle the event
                    await self.handle_event(event)
                    
                    # Calculate processing time
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    # Update average processing time
                    total_events = self.event_stats['events_processed']
                    current_avg = self.event_stats['average_processing_time']
                    self.event_stats['average_processing_time'] = (
                        (current_avg * total_events + processing_time) / (total_events + 1)
                    )
                else:
                    await asyncio.sleep(0.1)  # Small delay when queue is empty
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing event queue {event_type}: {e}")
                await asyncio.sleep(1)
    
    def get_event_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        queue_sizes = {
            event_type.name: len(queue) 
            for event_type, queue in self.event_queues.items()
        }
        
        return {
            'event_stats': self.event_stats.copy(),
            'active_handlers': len(self.event_handlers),
            'queue_sizes': queue_sizes,
            'processing_tasks': len(self.processing_tasks)
        }


class WorkflowOrchestrator:
    """Orchestrates workflows for agent coordination"""
    
    def __init__(self, event_bus: EventBus, redis_client: RedisPubSubClient,
                 message_router: MessageRouter):
        self.event_bus = event_bus
        self.redis = redis_client
        self.message_router = message_router
        
        # Active workflows
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_handlers: Dict[str, Callable] = {}
        
        # Workflow templates
        self.workflow_templates: Dict[str, Dict[str, Any]] = {}
        
        # Coordination requests
        self.coordination_requests: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self.workflow_lock = asyncio.Lock()
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the workflow orchestrator"""
        # Start workflow monitoring task
        self.monitoring_task = asyncio.create_task(self._monitor_workflows())
        
        # Register event handlers
        await self._register_event_handlers()
        
        self.logger.info("Workflow orchestrator started")
    
    async def stop(self):
        """Stop the workflow orchestrator"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        self.logger.info("Workflow orchestrator stopped")
    
    async def create_workflow(self, name: str, description: str, 
                            steps: List[Dict[str, Any]],
                            context: Dict[str, Any] = None) -> str:
        """Create a new workflow"""
        try:
            workflow_id = str(uuid.uuid4())
            
            workflow = Workflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                steps=steps,
                context=context or {}
            )
            
            # Store workflow
            self.active_workflows[workflow_id] = workflow
            
            # Publish workflow created event
            workflow_event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.WORKFLOW_STARTED,
                source="workflow_orchestrator",
                data={
                    'workflow_id': workflow_id,
                    'workflow_name': name,
                    'workflow_description': description,
                    'steps_count': len(steps)
                },
                correlation_id=workflow_id
            )
            
            await self.event_bus.publish_event(workflow_event)
            
            self.logger.info(f"Workflow {workflow_id} created: {name}")
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Failed to create workflow: {e}")
            raise
    
    async def execute_workflow(self, workflow_id: str, 
                             step_context: Dict[str, Any] = None) -> bool:
        """Execute a workflow"""
        try:
            if workflow_id not in self.active_workflows:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            workflow = self.active_workflows[workflow_id]
            
            # Update workflow status
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.utcnow()
            
            # Execute workflow steps
            await self._execute_workflow_steps(workflow, step_context or {})
            
            self.logger.info(f"Workflow {workflow_id} execution started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            return False
    
    async def coordinate_with_agents(self, workflow_id: str, step_id: str,
                                   coordination_request: Dict[str, Any]) -> str:
        """Coordinate with agents for workflow step"""
        try:
            request_id = str(uuid.uuid4())
            
            coordination_data = {
                'request_id': request_id,
                'workflow_id': workflow_id,
                'step_id': step_id,
                'request': coordination_request,
                'created_at': datetime.utcnow()
            }
            
            self.coordination_requests[request_id] = coordination_data
            
            # Send coordination request to agents
            coordination_message = ProtocolMessage(
                sender_id="workflow_orchestrator",
                channel="coordination",
                message_type=MessageType.COORDINATION_REQUEST,
                title=f"Workflow Coordination Request",
                content=json.dumps(coordination_data),
                priority=MessagePriority.HIGH,
                correlation_id=request_id
            )
            
            await self.message_router.route_message(coordination_message)
            
            # Start timeout monitoring
            asyncio.create_task(self._monitor_coordination_timeout(request_id))
            
            self.logger.debug(f"Coordination request {request_id} sent")
            return request_id
            
        except Exception as e:
            self.logger.error(f"Failed to coordinate with agents: {e}")
            raise
    
    async def handle_coordination_response(self, response_data: Dict[str, Any]) -> bool:
        """Handle coordination response from agents"""
        try:
            request_id = response_data.get('request_id')
            
            if request_id not in self.coordination_requests:
                self.logger.warning(f"Unknown coordination request: {request_id}")
                return False
            
            coordination_data = self.coordination_requests[request_id]
            workflow_id = coordination_data['workflow_id']
            step_id = coordination_data['step_id']
            
            # Update workflow step with response
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
                
                # Find and update the step
                for i, step_config in enumerate(workflow.steps):
                    if step_config.get('step_id') == step_id:
                        workflow.context[f'step_{step_id}_response'] = response_data
                        break
            
            # Remove coordination request
            del self.coordination_requests[request_id]
            
            # Publish coordination response event
            response_event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.COORDINATION_RESPONSE,
                source="workflow_orchestrator",
                data={
                    'request_id': request_id,
                    'workflow_id': workflow_id,
                    'step_id': step_id,
                    'response': response_data
                },
                correlation_id=workflow_id
            )
            
            await self.event_bus.publish_event(response_event)
            
            self.logger.debug(f"Coordination response {request_id} handled")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to handle coordination response: {e}")
            return False
    
    async def _execute_workflow_steps(self, workflow: Workflow, step_context: Dict[str, Any]):
        """Execute workflow steps"""
        try:
            # Convert step configs to WorkflowStep objects
            steps = []
            for step_config in workflow.steps:
                step = WorkflowStep(
                    step_id=step_config.get('step_id', str(uuid.uuid4())),
                    name=step_config.get('name', f"Step {len(steps) + 1}"),
                    action=step_config.get('action', ''),
                    parameters=step_config.get('parameters', {}),
                    dependencies=step_config.get('dependencies', []),
                    timeout=step_config.get('timeout', 60)
                )
                steps.append(step)
            
            # Execute steps based on dependencies
            executed_steps = set()
            while len(executed_steps) < len(steps):
                progress_made = False
                
                for step in steps:
                    if step.step_id in executed_steps:
                        continue
                    
                    # Check if dependencies are satisfied
                    if not all(dep in executed_steps for dep in step.dependencies):
                        continue
                    
                    # Execute step
                    await self._execute_workflow_step(workflow, step, step_context)
                    executed_steps.add(step.step_id)
                    progress_made = True
                    
                    # Check if step failed
                    if step.status == "failed":
                        workflow.status = WorkflowStatus.FAILED
                        return
                
                if not progress_made:
                    # Deadlock - can't execute any more steps
                    self.logger.warning(f"Workflow {workflow.workflow_id} has circular dependencies")
                    workflow.status = WorkflowStatus.FAILED
                    return
            
            # All steps completed successfully
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            
            # Publish workflow completion event
            completion_event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.WORKFLOW_COMPLETED,
                source="workflow_orchestrator",
                data={
                    'workflow_id': workflow.workflow_id,
                    'workflow_name': workflow.name,
                    'execution_time': (workflow.completed_at - workflow.started_at).total_seconds()
                },
                correlation_id=workflow.workflow_id
            )
            
            await self.event_bus.publish_event(completion_event)
            
        except Exception as e:
            self.logger.error(f"Failed to execute workflow steps: {e}")
            workflow.status = WorkflowStatus.FAILED
    
    async def _execute_workflow_step(self, workflow: Workflow, step: WorkflowStep, 
                                   step_context: Dict[str, Any]):
        """Execute a single workflow step"""
        try:
            step.status = "running"
            step.started_at = datetime.utcnow()
            
            self.logger.info(f"Executing workflow step {step.step_id}: {step.name}")
            
            # Determine action type and execute accordingly
            if step.action == "message":
                await self._execute_message_action(workflow, step, step_context)
            elif step.action == "coordination":
                await self._execute_coordination_action(workflow, step, step_context)
            elif step.action == "event":
                await self._execute_event_action(workflow, step, step_context)
            elif step.action == "delay":
                await self._execute_delay_action(workflow, step, step_context)
            else:
                # Custom action - delegate to handler
                handler = self.workflow_handlers.get(step.action)
                if handler:
                    step.result = await handler(workflow, step, step_context)
                else:
                    raise ValueError(f"Unknown action: {step.action}")
            
            step.status = "completed"
            step.completed_at = datetime.utcnow()
            
            self.logger.info(f"Workflow step {step.step_id} completed")
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.completed_at = datetime.utcnow()
            
            self.logger.error(f"Workflow step {step.step_id} failed: {e}")
    
    async def _execute_message_action(self, workflow: Workflow, step: WorkflowStep, 
                                    step_context: Dict[str, Any]):
        """Execute message action"""
        message_data = step.parameters.get('message', {})
        
        message = ProtocolMessage(
            sender_id="workflow_orchestrator",
            channel=message_data.get('channel', 'workflow'),
            message_type=MessageType(message_data.get('message_type', 'notification')),
            title=f"[WORKFLOW] {message_data.get('title', 'Workflow Message')}",
            content=message_data.get('content', ''),
            payload=message_data.get('payload', {}),
            priority=MessagePriority(step.parameters.get('priority', 2)),
            correlation_id=workflow.workflow_id
        )
        
        await self.message_router.route_message(message)
    
    async def _execute_coordination_action(self, workflow: Workflow, step: WorkflowStep, 
                                         step_context: Dict[str, Any]):
        """Execute coordination action"""
        coordination_data = step.parameters.get('coordination', {})
        
        request_id = await self.coordinate_with_agents(
            workflow.workflow_id, step.step_id, coordination_data
        )
        
        # Wait for response
        timeout = step.timeout
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).seconds < timeout:
            if request_id not in self.coordination_requests:
                break
            await asyncio.sleep(0.1)
        
        if request_id in self.coordination_requests:
            raise TimeoutError("Coordination request timed out")
        
        # Get response from workflow context
        step.result = workflow.context.get(f'step_{step.step_id}_response', {})
    
    async def _execute_event_action(self, workflow: Workflow, step: WorkflowStep, 
                                  step_context: Dict[str, Any]):
        """Execute event action"""
        event_data = step.parameters.get('event', {})
        
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType(event_data.get('event_type')),
            source="workflow_orchestrator",
            data=event_data.get('data', {}),
            correlation_id=workflow.workflow_id
        )
        
        await self.event_bus.publish_event(event)
    
    async def _execute_delay_action(self, workflow: Workflow, step: WorkflowStep, 
                                  step_context: Dict[str, Any]):
        """Execute delay action"""
        delay_seconds = step.parameters.get('delay_seconds', 1)
        await asyncio.sleep(delay_seconds)
    
    async def _monitor_workflows(self):
        """Monitor workflow execution and handle timeouts"""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Check for workflow timeouts
                for workflow_id, workflow in self.active_workflows.items():
                    if workflow.status == WorkflowStatus.RUNNING:
                        # Check if workflow has been running too long
                        if (current_time - workflow.started_at).seconds > 3600:  # 1 hour timeout
                            workflow.status = WorkflowStatus.FAILED
                            
                            # Publish workflow failed event
                            failure_event = Event(
                                event_id=str(uuid.uuid4()),
                                event_type=EventType.WORKFLOW_FAILED,
                                source="workflow_orchestrator",
                                data={
                                    'workflow_id': workflow_id,
                                    'reason': 'timeout'
                                },
                                correlation_id=workflow_id
                            )
                            
                            await self.event_bus.publish_event(failure_event)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring workflows: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_coordination_timeout(self, request_id: str):
        """Monitor coordination request timeout"""
        await asyncio.sleep(60)  # 60 second timeout
        
        if request_id in self.coordination_requests:
            coordination_data = self.coordination_requests[request_id]
            workflow_id = coordination_data['workflow_id']
            
            # Publish coordination timeout event
            timeout_event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.COORDINATION_RESPONSE,
                source="workflow_orchestrator",
                data={
                    'request_id': request_id,
                    'workflow_id': workflow_id,
                    'step_id': coordination_data['step_id'],
                    'response': {'error': 'timeout'},
                    'timed_out': True
                },
                correlation_id=workflow_id
            )
            
            await self.event_bus.publish_event(timeout_event)
            
            # Remove timeout request
            del self.coordination_requests[request_id]
    
    async def _register_event_handlers(self):
        """Register event handlers for workflow orchestration"""
        
        # Handle agent events
        await self.event_bus.subscribe_to_events(
            [EventType.AGENT_REGISTERED, EventType.AGENT_UNREGISTERED],
            self._handle_agent_events,
            priority=EventPriority.HIGH
        )
        
        # Handle message events
        await self.event_bus.subscribe_to_events(
            [EventType.MESSAGE_SENT, EventType.MESSAGE_DELIVERED, EventType.MESSAGE_FAILED],
            self._handle_message_events,
            priority=EventPriority.NORMAL
        )
    
    async def _handle_agent_events(self, event: Event):
        """Handle agent-related events"""
        self.logger.info(f"Agent event: {event.event_type.value} from {event.source}")
    
    async def _handle_message_events(self, event: Event):
        """Handle message-related events"""
        self.logger.debug(f"Message event: {event.event_type.value}")
    
    def register_workflow_handler(self, action_name: str, handler_func: Callable):
        """Register custom workflow action handler"""
        self.workflow_handlers[action_name] = handler_func
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow orchestrator statistics"""
        workflow_status_counts = defaultdict(int)
        for workflow in self.active_workflows.values():
            workflow_status_counts[workflow.status.value] += 1
        
        return {
            'active_workflows': len(self.active_workflows),
            'workflow_status_counts': dict(workflow_status_counts),
            'coordination_requests': len(self.coordination_requests),
            'workflow_templates': len(self.workflow_templates),
            'registered_handlers': len(self.workflow_handlers)
        }


# Example usage and integration
async def create_event_driven_system(redis_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a complete event-driven system"""
    # Initialize core components
    redis_client = RedisPubSubClient(**redis_config)
    await redis_client.connect()
    
    # Create message router
    message_router = MessageRouter(redis_client)
    await message_router.start()
    
    # Create message persistence
    message_persistence = MessagePersistence(redis_client)
    await message_persistence.start()
    
    # Create event bus
    event_bus = EventBus(redis_client)
    await event_bus.start()
    
    # Create workflow orchestrator
    workflow_orchestrator = WorkflowOrchestrator(
        event_bus, redis_client, message_router
    )
    await workflow_orchestrator.start()
    
    system = {
        'redis_client': redis_client,
        'message_router': message_router,
        'message_persistence': message_persistence,
        'event_bus': event_bus,
        'workflow_orchestrator': workflow_orchestrator
    }
    
    return system