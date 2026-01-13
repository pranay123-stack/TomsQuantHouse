"""
Event-driven architecture for agent coordination.
Provides event sourcing, event handling, and coordination mechanisms.
"""

from typing import Dict, Any, List, Optional, Callable, Set, Type, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import logging
import weakref
from collections import defaultdict, deque
import threading
import time
import copy

from schemas.message_schemas import (
    BaseMessage, MessageType, AgentCoordinationMessage,
    MessageFactory, AgentInfo
)

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events in the system"""
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    MESSAGE_FAILED = "message_failed"
    COORDINATION_STARTED = "coordination_started"
    COORDINATION_COMPLETED = "coordination_completed"
    COORDINATION_FAILED = "coordination_failed"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    PERFORMANCE_METRIC = "performance_metric"


class EventSeverity(Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CoordinationState(Enum):
    """Coordination state machine states"""
    INITIATED = "initiated"
    RECRUITING = "recruiting"
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Event:
    """System event representation"""
    event_id: str
    event_type: EventType
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    severity: EventSeverity = EventSeverity.INFO
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventHandler:
    """Event handler definition"""
    handler_id: str
    event_types: Set[EventType]
    handler_func: Callable[[Event], Any]
    priority: int = 0
    async_handler: bool = False
    enabled: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class CoordinationTask:
    """Coordination task definition"""
    task_id: str
    coordinator_id: str
    task_type: str
    participants: List[str]
    parameters: Dict[str, Any]
    state: CoordinationState = CoordinationState.INITIATED
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    timeout: int = 300
    retry_count: int = 0
    results: Dict[str, Any] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)


@dataclass
class WorkflowStep:
    """Workflow step definition"""
    step_id: str
    step_name: str
    step_type: str
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 60
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    compensation: Optional[str] = None  # Compensation step ID


@dataclass
class Workflow:
    """Workflow definition"""
    workflow_id: str
    workflow_name: str
    steps: Dict[str, WorkflowStep]
    entry_points: List[str] = field(default_factory=list)
    completion_criteria: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 3600
    compensation_strategy: str = "rollback"


class EventBus:
    """Central event bus for publishing and subscribing to events"""
    
    def __init__(self, event_bus_id: str = "default"):
        self.event_bus_id = event_bus_id
        self.handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self.event_history: deque = deque(maxlen=10000)
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.event_processor_task = None
        self.subscription_counts: Dict[EventType, int] = defaultdict(int)
        
        # Statistics
        self.stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'handler_invocations': 0,
            'average_processing_time': 0.0
        }
        
        # Thread safety
        self.lock = threading.RLock()
    
    async def start(self):
        """Start the event bus"""
        self.running = True
        self.event_processor_task = asyncio.create_task(self._event_processor_loop())
        logger.info(f"Event bus {self.event_bus_id} started")
    
    async def stop(self):
        """Stop the event bus"""
        self.running = False
        if self.event_processor_task:
            self.event_processor_task.cancel()
        logger.info(f"Event bus {self.event_bus_id} stopped")
    
    async def publish_event(self, event: Event) -> bool:
        """Publish an event to the event bus"""
        try:
            with self.lock:
                self.event_history.append(event)
                self.stats['events_published'] += 1
            
            # Add to processing queue
            await self.event_queue.put(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    def subscribe(self, event_types: List[EventType], handler: Callable[[Event], Any],
                 handler_id: Optional[str] = None, priority: int = 0,
                 async_handler: bool = False) -> str:
        """Subscribe to events"""
        if not handler_id:
            handler_id = f"handler_{uuid.uuid4().hex[:8]}"
        
        event_handler = EventHandler(
            handler_id=handler_id,
            event_types=set(event_types),
            handler_func=handler,
            priority=priority,
            async_handler=async_handler
        )
        
        with self.lock:
            for event_type in event_types:
                self.handlers[event_type].append(event_handler)
                self.subscription_counts[event_type] += 1
            
            # Sort handlers by priority
            for event_type in event_types:
                self.handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        
        logger.info(f"Subscribed handler {handler_id} to events: {[et.value for et in event_types]}")
        return handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler"""
        try:
            with self.lock:
                found = False
                for event_type, handlers in self.handlers.items():
                    for i, handler in enumerate(handlers):
                        if handler.handler_id == handler_id:
                            handlers.pop(i)
                            self.subscription_counts[event_type] -= 1
                            found = True
                            break
                
                if found:
                    logger.info(f"Unsubscribed handler {handler_id}")
                    return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe handler {handler_id}: {e}")
            return False
    
    def get_event_history(self, limit: int = 100, 
                         event_types: Optional[List[EventType]] = None,
                         since: Optional[datetime] = None) -> List[Event]:
        """Get event history with filtering"""
        with self.lock:
            events = list(self.event_history)
        
        # Filter by event types
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        # Filter by timestamp
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_bus_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self.lock:
            handler_counts = {et.value: len(handlers) for et, handlers in self.handlers.items()}
            
            return {
                'event_bus_id': self.event_bus_id,
                'total_handlers': sum(len(handlers) for handlers in self.handlers.values()),
                'subscription_counts': dict(self.subscription_counts),
                'handler_counts_by_type': handler_counts,
                'queue_size': self.event_queue.qsize(),
                'events_in_history': len(self.event_history),
                'statistics': self.stats.copy()
            }
    
    async def _event_processor_loop(self):
        """Background loop for processing events"""
        while self.running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Process event
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event processor: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_event(self, event: Event):
        """Process a single event"""
        start_time = time.time()
        
        try:
            # Get handlers for this event type
            handlers = self.handlers.get(event.event_type, [])
            
            # Invoke handlers
            for handler in handlers:
                if not handler.enabled:
                    continue
                
                try:
                    if handler.async_handler:
                        # Run async handler in background
                        asyncio.create_task(self._invoke_handler(handler, event))
                    else:
                        # Run sync handler in thread pool
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, handler.handler_func, event)
                    
                    self.stats['handler_invocations'] += 1
                    
                except Exception as e:
                    logger.error(f"Handler {handler.handler_id} failed: {e}")
                    # Implement retry logic here if needed
            
            self.stats['events_processed'] += 1
            
        except Exception as e:
            logger.error(f"Failed to process event: {e}")
            self.stats['events_failed'] += 1
        
        finally:
            # Update processing time statistics
            processing_time = time.time() - start_time
            current_avg = self.stats['average_processing_time']
            total_processed = self.stats['events_processed']
            
            if total_processed > 1:
                self.stats['average_processing_time'] = (
                    (current_avg * (total_processed - 1) + processing_time) / total_processed
                )
            else:
                self.stats['average_processing_time'] = processing_time
    
    async def _invoke_handler(self, handler: EventHandler, event: Event):
        """Invoke an event handler with error handling"""
        try:
            if asyncio.iscoroutinefunction(handler.handler_func):
                await handler.handler_func(event)
            else:
                handler.handler_func(event)
                
        except Exception as e:
            logger.error(f"Handler {handler.handler_id} execution failed: {e}")
            # Implement retry logic here


class CoordinationEngine:
    """Engine for coordinating multiple agents"""
    
    def __init__(self, engine_id: str, event_bus: EventBus):
        self.engine_id = engine_id
        self.event_bus = event_bus
        self.active_tasks: Dict[str, CoordinationTask] = {}
        self.task_history: deque = deque(maxlen=10000)
        self.participant_assignments: Dict[str, Set[str]] = defaultdict(set)
        
        # Workflow management
        self.workflows: Dict[str, Workflow] = {}
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Task processors
        self.task_processors: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            'tasks_started': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'active_tasks': 0,
            'workflows_executed': 0
        }
    
    async def start_coordination(self, coordinator_id: str, task_type: str,
                               participants: List[str], parameters: Dict[str, Any],
                               timeout: int = 300) -> str:
        """Start a coordination task"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Create coordination task
        task = CoordinationTask(
            task_id=task_id,
            coordinator_id=coordinator_id,
            task_type=task_type,
            participants=participants,
            parameters=parameters,
            deadline=datetime.now() + timedelta(seconds=timeout),
            timeout=timeout
        )
        
        self.active_tasks[task_id] = task
        self.participant_assignments[task_id] = set(participants)
        
        # Update statistics
        self.stats['tasks_started'] += 1
        self.stats['active_tasks'] += 1
        
        # Publish coordination started event
        await self.event_bus.publish_event(Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.COORDINATION_STARTED,
            source=self.engine_id,
            timestamp=datetime.now(),
            data={
                'task_id': task_id,
                'coordinator_id': coordinator_id,
                'task_type': task_type,
                'participants': participants,
                'parameters': parameters
            },
            correlation_id=task_id
        ))
        
        # Start task execution
        asyncio.create_task(self._execute_task(task))
        
        logger.info(f"Started coordination task {task_id} with {len(participants)} participants")
        return task_id
    
    async def _execute_task(self, task: CoordinationTask):
        """Execute a coordination task"""
        try:
            # Update state to recruiting
            task.state = CoordinationState.RECRUITING
            
            # Send coordination requests to participants
            recruitment_success = await self._recruit_participants(task)
            
            if not recruitment_success:
                task.state = CoordinationState.FAILED
                task.error_messages.append("Failed to recruit participants")
                return
            
            # Update state to active
            task.state = CoordinationState.ACTIVE
            
            # Execute task based on type
            processor = self.task_processors.get(task.task_type)
            if processor:
                await processor(task)
            else:
                # Generic coordination
                await self._generic_coordination(task)
            
            # Mark as completed
            task.state = CoordinationState.COMPLETED
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task.state = CoordinationState.FAILED
            task.error_messages.append(str(e))
        
        finally:
            # Update statistics and cleanup
            self.stats['active_tasks'] -= 1
            if task.state == CoordinationState.COMPLETED:
                self.stats['tasks_completed'] += 1
            else:
                self.stats['tasks_failed'] += 1
            
            # Add to history
            self.task_history.append(copy.deepcopy(task))
            
            # Remove from active tasks
            self.active_tasks.pop(task.task_id, None)
            
            # Publish completion event
            await self.event_bus.publish_event(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.COORDINATION_COMPLETED if task.state == CoordinationState.COMPLETED else EventType.COORDINATION_FAILED,
                source=self.engine_id,
                timestamp=datetime.now(),
                data={
                    'task_id': task.task_id,
                    'state': task.state.value,
                    'results': task.results,
                    'error_messages': task.error_messages
                },
                correlation_id=task.task_id
            ))
    
    async def _recruit_participants(self, task: CoordinationTask) -> bool:
        """Recruit participants for coordination task"""
        recruitment_results = {}
        
        # Send recruitment messages to all participants
        for participant_id in task.participants:
            try:
                recruitment_message = MessageFactory.create_coordination(
                    sender_id=self.engine_id,
                    action="participate",
                    task_id=task.task_id,
                    task_type=task.task_type,
                    parameters=task.parameters
                )
                recruitment_message.recipient_id = participant_id
                
                # In a real implementation, this would send through the transport layer
                # For now, we simulate immediate acceptance
                recruitment_results[participant_id] = "accepted"
                
            except Exception as e:
                logger.error(f"Failed to recruit participant {participant_id}: {e}")
                recruitment_results[participant_id] = "failed"
        
        # Check if enough participants accepted
        accepted_count = sum(1 for result in recruitment_results.values() if result == "accepted")
        required_count = task.parameters.get('min_participants', len(task.participants))
        
        if accepted_count >= required_count:
            # Update participant list to only those who accepted
            task.participants = [pid for pid, result in recruitment_results.items() if result == "accepted"]
            logger.info(f"Recruited {len(task.participants)} participants for task {task.task_id}")
            return True
        else:
            logger.warning(f"Only {accepted_count} participants accepted, need {required_count}")
            return False
    
    async def _generic_coordination(self, task: CoordinationTask):
        """Generic coordination logic"""
        # Wait for all participants to be ready
        await asyncio.sleep(0.1)  # Simulate coordination time
        
        # Simulate task execution
        participant_results = {}
        for participant_id in task.participants:
            # Simulate participant work
            await asyncio.sleep(0.05)
            participant_results[participant_id] = {
                "status": "completed",
                "result": f"Task completed by {participant_id}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Aggregate results
        task.results = {
            "participants": participant_results,
            "summary": f"Task {task.task_id} completed by {len(task.participants)} participants",
            "completion_time": datetime.now().isoformat()
        }
    
    async def cancel_task(self, task_id: str, reason: str = "cancelled") -> bool:
        """Cancel a coordination task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.state = CoordinationState.CANCELLED
            task.error_messages.append(f"Task cancelled: {reason}")
            
            # Notify participants
            for participant_id in task.participants:
                cancellation_message = MessageFactory.create_coordination(
                    sender_id=self.engine_id,
                    action="cancel",
                    task_id=task_id,
                    reason=reason
                )
                cancellation_message.recipient_id = participant_id
            
            return True
        
        return False
    
    def register_task_processor(self, task_type: str, processor: Callable[[CoordinationTask], Any]):
        """Register a task processor for specific task types"""
        self.task_processors[task_type] = processor
    
    def get_task_status(self, task_id: str) -> Optional[CoordinationTask]:
        """Get status of a coordination task"""
        return self.active_tasks.get(task_id)
    
    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination engine statistics"""
        return {
            'engine_id': self.engine_id,
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.task_history),
            'task_statistics': self.stats.copy(),
            'task_processors_registered': len(self.task_processors),
            'participant_assignments': {k: len(v) for k, v in self.participant_assignments.items()}
        }


class WorkflowEngine:
    """Engine for executing complex workflows with multiple steps"""
    
    def __init__(self, engine_id: str, event_bus: EventBus):
        self.engine_id = engine_id
        self.event_bus = event_bus
        self.workflows: Dict[str, Workflow] = {}
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.step_processors: Dict[str, Callable] = {}
        
    def register_workflow(self, workflow: Workflow):
        """Register a workflow definition"""
        self.workflows[workflow.workflow_id] = workflow
        logger.info(f"Registered workflow {workflow.workflow_id} with {len(workflow.steps)} steps")
    
    async def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any],
                             execution_id: Optional[str] = None) -> str:
        """Execute a workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        if not execution_id:
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        workflow = self.workflows[workflow_id]
        
        execution = {
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'parameters': parameters,
            'state': 'running',
            'started_at': datetime.now(),
            'step_results': {},
            'current_step': None,
            'error': None
        }
        
        self.active_executions[execution_id] = execution
        
        # Start workflow execution
        asyncio.create_task(self._execute_workflow_steps(execution, workflow))
        
        return execution_id
    
    async def _execute_workflow_steps(self, execution: Dict[str, Any], workflow: Workflow):
        """Execute workflow steps"""
        try:
            execution['state'] = 'running'
            
            # Get execution order based on dependencies
            execution_order = self._calculate_execution_order(workflow)
            
            # Execute steps in order
            for step_id in execution_order:
                step = workflow.steps[step_id]
                execution['current_step'] = step_id
                
                try:
                    # Check dependencies
                    if not await self._check_step_dependencies(step, execution):
                        raise Exception(f"Dependencies not satisfied for step {step_id}")
                    
                    # Execute step
                    step_result = await self._execute_step(step, execution)
                    execution['step_results'][step_id] = step_result
                    
                    logger.debug(f"Completed step {step_id} in workflow execution {execution['execution_id']}")
                    
                except Exception as e:
                    logger.error(f"Step {step_id} failed: {e}")
                    
                    # Try compensation if defined
                    if step.compensation:
                        await self._execute_compensation(step.compensation, execution)
                    
                    execution['error'] = str(e)
                    execution['state'] = 'failed'
                    break
            
            if execution['state'] != 'failed':
                execution['state'] = 'completed'
                execution['completed_at'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution['error'] = str(e)
            execution['state'] = 'failed'
        
        finally:
            # Publish completion event
            await self.event_bus.publish_event(Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.COORDINATION_COMPLETED,
                source=self.engine_id,
                timestamp=datetime.now(),
                data={
                    'execution_id': execution['execution_id'],
                    'workflow_id': execution['workflow_id'],
                    'state': execution['state'],
                    'error': execution.get('error')
                }
            ))
    
    def _calculate_execution_order(self, workflow: Workflow) -> List[str]:
        """Calculate step execution order based on dependencies"""
        # Simple topological sort
        visited = set()
        visiting = set()
        order = []
        
        def visit(step_id: str):
            if step_id in visiting:
                raise Exception(f"Circular dependency detected involving step {step_id}")
            
            if step_id in visited:
                return
            
            visiting.add(step_id)
            
            step = workflow.steps[step_id]
            for dependency in step.dependencies:
                if dependency not in workflow.steps:
                    raise Exception(f"Unknown dependency {dependency} for step {step_id}")
                visit(dependency)
            
            visiting.remove(step_id)
            visited.add(step_id)
            order.append(step_id)
        
        # Start with entry points or all steps if no entry points
        start_steps = workflow.entry_points or list(workflow.steps.keys())
        
        for step_id in start_steps:
            if step_id in workflow.steps:
                visit(step_id)
        
        return order
    
    async def _check_step_dependencies(self, step: WorkflowStep, execution: Dict[str, Any]) -> bool:
        """Check if step dependencies are satisfied"""
        for dependency in step.dependencies:
            if dependency not in execution['step_results']:
                return False
        return True
    
    async def _execute_step(self, step: WorkflowStep, execution: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step"""
        processor = self.step_processors.get(step.step_type)
        if not processor:
            raise Exception(f"No processor registered for step type {step.step_type}")
        
        # Execute step with timeout
        return await asyncio.wait_for(
            processor(step, execution),
            timeout=step.timeout
        )
    
    async def _execute_compensation(self, compensation_step_id: str, execution: Dict[str, Any]):
        """Execute compensation step"""
        if compensation_step_id in self.workflows['default'].steps:  # Assume default workflow
            compensation_step = self.workflows['default'].steps[compensation_step_id]
            await self._execute_step(compensation_step, execution)
    
    def register_step_processor(self, step_type: str, processor: Callable[[WorkflowStep, Dict[str, Any]], Any]):
        """Register a processor for specific step types"""
        self.step_processors[step_type] = processor


# Example usage and factory functions
async def create_default_event_system(system_id: str = "default") -> Tuple[EventBus, CoordinationEngine, WorkflowEngine]:
    """Create default event-driven system"""
    event_bus = EventBus(f"event_bus_{system_id}")
    coordination_engine = CoordinationEngine(f"coordination_{system_id}", event_bus)
    workflow_engine = WorkflowEngine(f"workflow_{system_id}", event_bus)
    
    # Start event bus
    await event_bus.start()
    
    return event_bus, coordination_engine, workflow_engine


# Default event handlers
def create_default_event_handlers(registry=None, persistor=None):
    """Create default event handlers"""
    
    async def agent_registration_handler(event: Event):
        """Handle agent registration events"""
        if event.event_type == EventType.AGENT_REGISTERED:
            logger.info(f"Agent {event.data['agent_id']} registered")
    
    async def coordination_handler(event: Event):
        """Handle coordination events"""
        if event.event_type == EventType.COORDINATION_STARTED:
            logger.info(f"Coordination started: {event.data['task_id']}")
        elif event.event_type == EventType.COORDINATION_COMPLETED:
            logger.info(f"Coordination completed: {event.data['task_id']}")
    
    return [agent_registration_handler, coordination_handler]