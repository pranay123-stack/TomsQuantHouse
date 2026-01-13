"""
Communication protocols for agent interactions.
Defines standard communication patterns, request-response flows, and coordination mechanisms.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json
import sys
import os

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '..'))

from schemas.message_schemas import (
    BaseMessage, MessageType, Priority, DeliveryGuarantee, 
    MessageFactory, AgentInfo
)


class CommunicationPattern(Enum):
    """Types of communication patterns"""
    PUBLISH_SUBSCRIBE = "pub_sub"
    REQUEST_RESPONSE = "request_response"
    BROADCAST = "broadcast"
    POINT_TO_POINT = "point_to_point"
    AGGREGATION = "aggregation"
    SCATTER_GATHER = "scatter_gather"
    PIPELINE = "pipeline"


class ProtocolPhase(Enum):
    """Protocol execution phases"""
    INITIATION = "initiation"
    NEGOTIATION = "negotiation"
    EXECUTION = "execution"
    COORDINATION = "coordination"
    TERMINATION = "termination"
    ERROR_HANDLING = "error_handling"


@dataclass
class ProtocolContext:
    """Context information for protocol execution"""
    protocol_id: str
    participants: List[str]
    start_time: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    timeout: Optional[int] = None
    state: ProtocolPhase = ProtocolPhase.INITIATION
    variables: Dict[str, Any] = field(default_factory=dict)
    callbacks: Dict[str, Callable] = field(default_factory=dict)


@dataclass
class CoordinationRequest:
    """Request for agent coordination"""
    request_id: str
    coordinator_id: str
    action: str
    target_agents: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[datetime] = None
    timeout: int = 30
    priority: Priority = Priority.NORMAL


@dataclass
class CoordinationResponse:
    """Response to coordination request"""
    request_id: str
    agent_id: str
    status: str  # 'accepted', 'rejected', 'busy', 'error'
    response_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: Optional[float] = None


class AgentProtocol:
    """Base class for agent communication protocols"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.protocols: Dict[str, ProtocolContext] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.active_coordinations: Dict[str, CoordinationRequest] = {}
    
    async def send_message(self, message: BaseMessage, transport: Any) -> bool:
        """Send a message through the transport layer"""
        try:
            # Apply protocol-specific transformations
            transformed_message = await self._transform_message(message)
            
            # Send through transport
            success = await transport.send(transformed_message)
            
            # Log protocol activity
            await self._log_protocol_activity("message_sent", {
                "message_id": message.metadata.message_id,
                "recipient": message.recipient_id,
                "success": success
            })
            
            return success
        except Exception as e:
            await self._log_protocol_activity("message_error", {
                "message_id": message.metadata.message_id,
                "error": str(e)
            })
            return False
    
    async def handle_message(self, message: BaseMessage, transport: Any) -> Optional[BaseMessage]:
        """Handle incoming message based on protocol"""
        try:
            # Route message to appropriate handler
            handler = self._get_message_handler(message)
            if handler:
                response = await handler(message, transport)
                return response
            
            return None
        except Exception as e:
            await self._log_protocol_activity("message_handling_error", {
                "message_id": message.metadata.message_id,
                "error": str(e)
            })
            return None
    
    async def start_coordination(self, request: CoordinationRequest, transport: Any) -> str:
        """Start a coordination protocol"""
        coordination_id = f"{request.request_id}_{len(self.active_coordinations)}"
        self.active_coordinations[coordination_id] = request
        
        # Create protocol context
        context = ProtocolContext(
            protocol_id=coordination_id,
            participants=[request.coordinator_id] + request.target_agents,
            timeout=request.timeout
        )
        self.protocols[coordination_id] = context
        
        # Send coordination requests to target agents
        for agent_id in request.target_agents:
            coordination_message = MessageFactory.create_coordination(
                sender_id=self.agent_id,
                action="coordinate",
                request_id=request.request_id,
                coordination_type=request.action,
                parameters=request.parameters
            )
            coordination_message.recipient_id = agent_id
            coordination_message.metadata.correlation_id = coordination_id
            
            await self.send_message(coordination_message, transport)
        
        await self._log_protocol_activity("coordination_started", {
            "coordination_id": coordination_id,
            "action": request.action,
            "participants": context.participants
        })
        
        return coordination_id
    
    async def _transform_message(self, message: BaseMessage) -> BaseMessage:
        """Apply protocol-specific transformations to message"""
        # Default implementation - subclasses can override
        return message
    
    def _get_message_handler(self, message: BaseMessage) -> Optional[Callable]:
        """Get message handler based on message type"""
        handler_key = f"{message.message_type.value}_{message.metadata.correlation_id or 'default'}"
        return self.message_handlers.get(handler_key)
    
    async def _log_protocol_activity(self, activity: str, data: Dict[str, Any]):
        """Log protocol activity for monitoring"""
        # Default implementation - can be overridden
        print(f"[{activity}] {self.agent_id}: {data}")


class RequestResponseProtocol(AgentProtocol):
    """Request-response communication protocol"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.pending_requests: Dict[str, datetime] = {}
        self.response_handlers: Dict[str, Callable] = {}
    
    async def send_request(self, request: BaseMessage, response_handler: Callable,
                          timeout: int = 30, transport: Any = None) -> str:
        """Send request and set up response handling"""
        request.metadata.delivery_guarantee = DeliveryGuarantee.AT_LEAST_ONCE
        request.metadata.correlation_id = request.metadata.message_id
        
        # Store request for tracking
        self.pending_requests[request.metadata.message_id] = datetime.now()
        self.response_handlers[request.metadata.message_id] = response_handler
        
        # Send request
        if transport:
            await self.send_message(request, transport)
        
        # Set up timeout
        if timeout > 0:
            asyncio.create_task(self._handle_timeout(request.metadata.message_id, timeout))
        
        await self._log_protocol_activity("request_sent", {
            "request_id": request.metadata.message_id,
            "recipient": request.recipient_id
        })
        
        return request.metadata.message_id
    
    async def handle_response(self, response: BaseMessage) -> bool:
        """Handle incoming response"""
        correlation_id = response.metadata.correlation_id
        
        if correlation_id in self.response_handlers:
            handler = self.response_handlers[correlation_id]
            
            try:
                await handler(response)
                
                # Clean up
                del self.response_handlers[correlation_id]
                self.pending_requests.pop(correlation_id, None)
                
                await self._log_protocol_activity("response_received", {
                    "correlation_id": correlation_id
                })
                
                return True
            except Exception as e:
                await self._log_protocol_activity("response_handling_error", {
                    "correlation_id": correlation_id,
                    "error": str(e)
                })
                return False
        
        return False
    
    async def _handle_timeout(self, request_id: str, timeout: int):
        """Handle request timeout"""
        await asyncio.sleep(timeout)
        
        if request_id in self.pending_requests:
            # Request timed out
            handler = self.response_handlers.get(request_id)
            if handler:
                timeout_response = BaseMessage(
                    message_type=MessageType.STATUS,
                    sender_id="timeout_handler",
                    payload={
                        "status": "timeout",
                        "error": f"Request {request_id} timed out after {timeout} seconds"
                    },
                    metadata=MessageMetadata(correlation_id=request_id)
                )
                
                try:
                    await handler(timeout_response)
                except Exception as e:
                    print(f"Error handling timeout for {request_id}: {e}")
            
            # Clean up
            del self.response_handlers[request_id]
            self.pending_requests.pop(request_id, None)
            
            await self._log_protocol_activity("request_timeout", {
                "request_id": request_id,
                "timeout": timeout
            })


class PublishSubscribeProtocol(AgentProtocol):
    """Publish-subscribe communication protocol"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.subscriptions: Dict[str, List[str]] = {}  # channel -> agent_ids
        self.publisher_handlers: Dict[str, Callable] = {}
    
    async def publish(self, channel: str, message: BaseMessage, transport: Any = None) -> int:
        """Publish message to channel"""
        message.channel = channel
        message.metadata.routing_key = f"{channel}.{message.message_type.value}"
        
        # Get subscribers
        subscribers = self.subscriptions.get(channel, [])
        
        if transport:
            await self.send_message(message, transport)
        
        await self._log_protocol_activity("message_published", {
            "channel": channel,
            "message_id": message.metadata.message_id,
            "subscriber_count": len(subscribers)
        })
        
        return len(subscribers)
    
    def subscribe(self, channel: str, agent_id: str):
        """Subscribe agent to channel"""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        
        if agent_id not in self.subscriptions[channel]:
            self.subscriptions[channel].append(agent_id)
        
        self._log_protocol_activity("agent_subscribed", {
            "channel": channel,
            "agent_id": agent_id
        })
    
    def unsubscribe(self, channel: str, agent_id: str):
        """Unsubscribe agent from channel"""
        if channel in self.subscriptions and agent_id in self.subscriptions[channel]:
            self.subscriptions[channel].remove(agent_id)
            
            self._log_protocol_activity("agent_unsubscribed", {
                "channel": channel,
                "agent_id": agent_id
            })
    
    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get subscribers for a channel"""
        return self.subscriptions.get(channel, [])


class CoordinationProtocol(AgentProtocol):
    """Agent coordination protocol for collaborative tasks"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.coordination_participants: Dict[str, List[str]] = {}
        self.coordination_results: Dict[str, Dict[str, Any]] = {}
    
    async def initiate_coordination(self, action: str, participants: List[str],
                                  parameters: Dict[str, Any], transport: Any = None) -> str:
        """Initiate coordination among multiple agents"""
        coordination_id = f"coord_{action}_{len(self.coordination_participants)}"
        self.coordination_participants[coordination_id] = participants
        
        # Create coordination request
        coordination_request = CoordinationRequest(
            request_id=coordination_id,
            coordinator_id=self.agent_id,
            action=action,
            target_agents=participants,
            parameters=parameters
        )
        
        # Send to all participants
        for agent_id in participants:
            coordination_message = MessageFactory.create_coordination(
                sender_id=self.agent_id,
                action=action,
                coordination_id=coordination_id,
                parameters=parameters,
                participants=participants
            )
            coordination_message.recipient_id = agent_id
            
            if transport:
                await self.send_message(coordination_message, transport)
        
        self.active_coordinations[coordination_id] = coordination_request
        
        await self._log_protocol_activity("coordination_initiated", {
            "coordination_id": coordination_id,
            "action": action,
            "participants": participants
        })
        
        return coordination_id
    
    async def handle_coordination_request(self, message: BaseMessage) -> CoordinationResponse:
        """Handle incoming coordination request"""
        coordination_id = message.payload.get('coordination_id', 'unknown')
        action = message.payload.get('coordination_type', 'unknown')
        participants = message.payload.get('participants', [])
        
        # Check if we can participate
        can_participate = await self._can_participate(action, message.payload.get('parameters', {}))
        
        if can_participate:
            status = "accepted"
            # Add ourselves as participant if not already included
            if self.agent_id not in participants:
                participants.append(self.agent_id)
                self.coordination_participants[coordination_id] = participants
            
            response_data = {"participants": participants}
        else:
            status = "rejected"
            response_data = {"reason": "busy_or_unavailable"}
        
        return CoordinationResponse(
            request_id=coordination_id,
            agent_id=self.agent_id,
            status=status,
            response_data=response_data
        )
    
    async def complete_coordination(self, coordination_id: str, result: Dict[str, Any]):
        """Complete coordination and notify all participants"""
        if coordination_id in self.coordination_participants:
            participants = self.coordination_participants[coordination_id]
            self.coordination_results[coordination_id] = result
            
            await self._log_protocol_activity("coordination_completed", {
                "coordination_id": coordination_id,
                "result": result,
                "participants": participants
            })
            
            # Clean up
            del self.coordination_participants[coordination_id]
            del self.active_coordinations[coordination_id]
    
    async def _can_participate(self, action: str, parameters: Dict[str, Any]) -> bool:
        """Check if agent can participate in coordination"""
        # Default implementation - override in specific agents
        return True


class DiscoveryProtocol(AgentProtocol):
    """Agent discovery protocol for finding and registering agents"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.registered_agents: Dict[str, AgentInfo] = {}
        self.discovery_handlers: Dict[str, Callable] = {}
    
    async def register_agent(self, agent_info: AgentInfo, transport: Any = None) -> bool:
        """Register agent in the discovery registry"""
        self.registered_agents[agent_info.agent_id] = agent_info
        
        # Broadcast registration to other agents
        registration_message = MessageFactory.create_discovery(
            sender_id=self.agent_id,
            discovery_type="registration",
            agent_info={
                "agent_id": agent_info.agent_id,
                "agent_type": agent_info.agent_type,
                "capabilities": agent_info.capabilities,
                "endpoint": agent_info.endpoint,
                "version": agent_info.version,
                "metadata": agent_info.metadata
            }
        )
        
        if transport:
            await self.send_message(registration_message, transport)
        
        await self._log_protocol_activity("agent_registered", {
            "agent_id": agent_info.agent_id,
            "agent_type": agent_info.agent_type,
            "capabilities": agent_info.capabilities
        })
        
        return True
    
    async def discover_agents(self, criteria: Dict[str, Any], transport: Any = None) -> List[AgentInfo]:
        """Discover agents matching criteria"""
        discovery_message = MessageFactory.create_discovery(
            sender_id=self.agent_id,
            discovery_type="query",
            criteria=criteria
        )
        
        if transport:
            await self.send_message(discovery_message, transport)
        
        # Filter locally registered agents
        matching_agents = []
        for agent_info in self.registered_agents.values():
            if self._matches_criteria(agent_info, criteria):
                matching_agents.append(agent_info)
        
        await self._log_protocol_activity("agent_discovery", {
            "criteria": criteria,
            "results_count": len(matching_agents)
        })
        
        return matching_agents
    
    async def handle_discovery_request(self, message: BaseMessage) -> Optional[BaseMessage]:
        """Handle agent discovery request"""
        discovery_type = message.payload.get('type')
        
        if discovery_type == 'query':
            criteria = message.payload.get('criteria', {})
            matching_agents = []
            
            # Filter agents by criteria
            for agent_info in self.registered_agents.values():
                if self._matches_criteria(agent_info, criteria):
                    matching_agents.append({
                        "agent_id": agent_info.agent_id,
                        "agent_type": agent_info.agent_type,
                        "capabilities": agent_info.capabilities,
                        "endpoint": agent_info.endpoint,
                        "version": agent_info.version
                    })
            
            # Send response
            response = MessageFactory.create_discovery(
                sender_id=self.agent_id,
                discovery_type="response",
                results=matching_agents,
                correlation_id=message.metadata.correlation_id
            )
            response.recipient_id = message.sender_id
            
            return response
        
        elif discovery_type == 'registration':
            agent_data = message.payload.get('agent_info', {})
            if agent_data:
                agent_info = AgentInfo(
                    agent_id=agent_data['agent_id'],
                    agent_type=agent_data['agent_type'],
                    capabilities=agent_data['capabilities'],
                    endpoint=agent_data['endpoint'],
                    version=agent_data.get('version', '1.0'),
                    metadata=agent_data.get('metadata', {})
                )
                self.registered_agents[agent_info.agent_id] = agent_info
        
        return None
    
    def _matches_criteria(self, agent_info: AgentInfo, criteria: Dict[str, Any]) -> bool:
        """Check if agent matches discovery criteria"""
        # Check agent type
        if 'agent_type' in criteria and agent_info.agent_type != criteria['agent_type']:
            return False
        
        # Check capabilities
        if 'capabilities' in criteria:
            required_capabilities = criteria['capabilities']
            if not all(cap in agent_info.capabilities for cap in required_capabilities):
                return False
        
        # Check version
        if 'min_version' in criteria:
            # Simple version comparison - should be more sophisticated
            if agent_info.version < criteria['min_version']:
                return False
        
        return True


# Protocol factory
class ProtocolFactory:
    """Factory for creating communication protocols"""
    
    @staticmethod
    def create_protocol(pattern: CommunicationPattern, agent_id: str) -> AgentProtocol:
        """Create protocol instance based on pattern"""
        if pattern == CommunicationPattern.REQUEST_RESPONSE:
            return RequestResponseProtocol(agent_id)
        elif pattern == CommunicationPattern.PUBLISH_SUBSCRIBE:
            return PublishSubscribeProtocol(agent_id)
        elif pattern == CommunicationPattern.AGGREGATION:
            return CoordinationProtocol(agent_id)
        elif pattern == CommunicationPattern.SCATTER_GATHER:
            return CoordinationProtocol(agent_id)
        elif pattern == CommunicationPattern.POINT_TO_POINT:
            return RequestResponseProtocol(agent_id)
        else:
            return AgentProtocol(agent_id)


# Protocol composition for complex scenarios
class ProtocolOrchestrator:
    """Orchestrates multiple protocols for complex communication scenarios"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.protocols: Dict[CommunicationPattern, AgentProtocol] = {}
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
    
    def add_protocol(self, pattern: CommunicationPattern) -> AgentProtocol:
        """Add a protocol to the orchestrator"""
        protocol = ProtocolFactory.create_protocol(pattern, self.agent_id)
        self.protocols[pattern] = protocol
        return protocol
    
    def get_protocol(self, pattern: CommunicationPattern) -> Optional[AgentProtocol]:
        """Get protocol by pattern"""
        return self.protocols.get(pattern)
    
    async def route_message(self, message: BaseMessage, transport: Any) -> Optional[BaseMessage]:
        """Route message through appropriate protocol"""
        # Determine best protocol based on message characteristics
        protocol = self._select_protocol(message)
        
        if protocol:
            return await protocol.handle_message(message, transport)
        
        return None
    
    def _select_protocol(self, message: BaseMessage) -> Optional[AgentProtocol]:
        """Select appropriate protocol for message"""
        # Select based on message type and delivery guarantee
        if message.metadata.delivery_guarantee == DeliveryGuarantee.EXACTLY_ONCE:
            return self.protocols.get(CommunicationPattern.REQUEST_RESPONSE)
        elif message.message_type == MessageType.DISCOVERY:
            return self.protocols.get(CommunicationPattern.BROADCAST)
        elif message.recipient_id:
            return self.protocols.get(CommunicationPattern.POINT_TO_POINT)
        else:
            return self.protocols.get(CommunicationPattern.PUBLISH_SUBSCRIBE)
    
    async def coordinate_complex_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate complex operations using multiple protocols"""
        operation_id = operation.get('id', 'unknown')
        
        try:
            # Start coordination protocol
            coordination_protocol = self.get_protocol(CommunicationPattern.AGGREGATION)
            if coordination_protocol:
                coordination_id = await coordination_protocol.initiate_coordination(
                    action=operation.get('action'),
                    participants=operation.get('participants', []),
                    parameters=operation.get('parameters', {})
                )
            
            # Use publish-subscribe for broadcasting updates
            pubsub_protocol = self.get_protocol(CommunicationPattern.PUBLISH_SUBSCRIBE)
            if pubsub_protocol:
                await pubsub_protocol.publish(
                    channel=f"operations.{operation_id}",
                    message=MessageFactory.create_coordination(
                        sender_id=self.agent_id,
                        action="status_update",
                        operation_id=operation_id,
                        status="started"
                    )
                )
            
            # Collect results
            results = await self._collect_operation_results(operation_id, operation)
            
            return {
                "operation_id": operation_id,
                "status": "completed",
                "results": results
            }
            
        except Exception as e:
            return {
                "operation_id": operation_id,
                "status": "error",
                "error": str(e)
            }
    
    async def _collect_operation_results(self, operation_id: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Collect results from distributed operation"""
        # This is a placeholder - implement based on specific requirements
        return {"status": "collected", "operation": operation}
