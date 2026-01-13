#!/usr/bin/env python3
"""
Multi-Agent Communication System via Letta REST API
Enables agents to communicate, share memory, and coordinate actions
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import queue
import asyncio
import aiohttp

from letta_client import LettaClient
from advanced_memory_manager import (
    AdvancedMemoryManager,
    MemoryBlockType,
    MemoryPriority,
    TradingPattern,
    MarketLearning
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages between agents"""
    DIRECT_MESSAGE = "direct_message"
    BROADCAST = "broadcast"
    MEMORY_SHARE = "memory_share"
    STRATEGY_REQUEST = "strategy_request"
    PERFORMANCE_UPDATE = "performance_update"
    RISK_ALERT = "risk_alert"
    COORDINATION_REQUEST = "coordination_request"
    LEARNING_UPDATE = "learning_update"
    STATUS_UPDATE = "status_update"


class CommunicationPriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class AgentRole(Enum):
    """Roles agents can play in communication"""
    STRATEGIST = "strategist"
    ANALYST = "analyst"
    RISK_MANAGER = "risk_manager"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    OBSERVER = "observer"


@dataclass
class AgentMessage:
    """Message structure for agent communication"""
    message_id: str
    sender_agent_id: str
    receiver_agent_id: Optional[str]  # None for broadcast
    message_type: MessageType
    priority: CommunicationPriority
    subject: str
    content: str
    attachments: List[Dict[str, Any]]
    timestamp: datetime
    expires_at: Optional[datetime]
    correlation_id: Optional[str]
    reply_to: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class MemoryShare:
    """Memory sharing specification"""
    memory_block_ids: List[str]
    access_level: str  # read, write, admin
    duration: timedelta
    sharing_agent_id: str
    recipient_agent_id: str
    conditions: Dict[str, Any]


@dataclass
class CoordinationRequest:
    """Request for agent coordination"""
    request_id: str
    requesting_agent: str
    target_agents: List[str]
    coordination_type: str  # strategy_validation, risk_assessment, etc.
    parameters: Dict[str, Any]
    deadline: datetime
    required_responses: int


@dataclass
class CommunicationStats:
    """Statistics about agent communication"""
    total_messages_sent: int
    total_messages_received: int
    messages_by_type: Dict[MessageType, int]
    average_response_time: float
    active_connections: int
    memory_shares_active: int
    coordination_requests_active: int


class AgentRegistry:
    """Registry of active agents"""
    
    def __init__(self):
        self.agents = {}
        self.agent_last_seen = {}
        self.agent_capabilities = {}
        self.communication_channels = {}
    
    def register_agent(self, agent_id: str, role: AgentRole, capabilities: List[str]):
        """Register an agent in the registry"""
        self.agents[agent_id] = {
            "role": role,
            "capabilities": capabilities,
            "registered_at": datetime.now(),
            "status": "active"
        }
        self.agent_last_seen[agent_id] = datetime.now()
        logger.info(f"Registered agent {agent_id} with role {role.value}")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
        if agent_id in self.agent_last_seen:
            del self.agent_last_seen[agent_id]
        if agent_id in self.agent_capabilities:
            del self.agent_capabilities[agent_id]
        logger.info(f"Unregistered agent {agent_id}")
    
    def update_agent_heartbeat(self, agent_id: str):
        """Update agent last seen timestamp"""
        self.agent_last_seen[agent_id] = datetime.now()
    
    def get_active_agents(self, role: AgentRole = None) -> List[str]:
        """Get list of active agents"""
        active_agents = []
        current_time = datetime.now()
        
        for agent_id, last_seen in self.agent_last_seen.items():
            # Consider agent active if seen in last 5 minutes
            if (current_time - last_seen).total_seconds() < 300:
                if role is None or self.agents.get(agent_id, {}).get("role") == role:
                    active_agents.append(agent_id)
        
        return active_agents
    
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents with specific capability"""
        matching_agents = []
        for agent_id, info in self.agents.items():
            if capability in info.get("capabilities", []):
                matching_agents.append(agent_id)
        return matching_agents
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information"""
        return self.agents.get(agent_id)


class MessageRouter:
    """Routes messages between agents"""
    
    def __init__(self, agent_registry: AgentRegistry):
        self.agent_registry = agent_registry
        self.message_queue = queue.PriorityQueue()
        self.message_handlers = {}
        self.routing_rules = {}
        self.blocked_senders = set()
        self.message_history = []
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """Register message handler for specific type"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for {message_type.value}")
    
    def add_routing_rule(self, pattern: str, target_agents: List[str]):
        """Add routing rule for message patterns"""
        self.routing_rules[pattern] = target_agents
    
    def route_message(self, message: AgentMessage) -> List[str]:
        """Route message to appropriate recipients"""
        
        recipients = []
        
        # Direct message
        if message.receiver_agent_id:
            recipients = [message.receiver_agent_id]
        
        # Broadcast
        elif message.message_type == MessageType.BROADCAST:
            recipients = self.agent_registry.get_active_agents()
            if message.sender_agent_id in recipients:
                recipients.remove(message.sender_agent_id)  # Don't send to self
        
        # Memory share
        elif message.message_type == MessageType.MEMORY_SHARE:
            if "recipient_agent_id" in message.metadata:
                recipients = [message.metadata["recipient_agent_id"]]
        
        # Strategy request
        elif message.message_type == MessageType.STRATEGY_REQUEST:
            # Find agents with strategy capability
            recipients = self.agent_registry.find_agents_by_capability("strategy")
        
        # Risk alert
        elif message.message_type == MessageType.RISK_ALERT:
            # Send to risk managers and coordinators
            risk_managers = self.agent_registry.get_active_agents(AgentRole.RISK_MANAGER)
            coordinators = self.agent_registry.get_active_agents(AgentRole.COORDINATOR)
            recipients = risk_managers + coordinators
        
        # Apply routing rules
        for pattern, rule_targets in self.routing_rules.items():
            if pattern.lower() in message.subject.lower() or pattern.lower() in message.content.lower():
                recipients.extend(rule_targets)
        
        # Remove blocked senders
        recipients = [r for r in recipients if r not in self.blocked_senders]
        
        # Remove duplicates
        recipients = list(set(recipients))
        
        return recipients
    
    def handle_message(self, message: AgentMessage):
        """Handle incoming message"""
        
        # Add to history
        self.message_history.append({
            "message_id": message.message_id,
            "timestamp": message.timestamp,
            "sender": message.sender_agent_id,
            "type": message.message_type.value,
            "subject": message.subject
        })
        
        # Keep only recent messages in history
        if len(self.message_history) > 1000:
            self.message_history = self.message_history[-500:]
        
        # Route message
        recipients = self.route_message(message)
        
        # Execute message handlers
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                handler(message, recipients)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
        
        return recipients


class MultiAgentCommunication:
    """Main multi-agent communication system"""
    
    def __init__(self, 
                 letta_client: LettaClient,
                 memory_manager: AdvancedMemoryManager,
                 redis_archival=None):
        
        self.letta_client = letta_client
        self.memory_manager = memory_manager
        self.redis_archival = redis_archival
        
        # Core components
        self.agent_registry = AgentRegistry()
        self.message_router = MessageRouter(self.agent_registry)
        
        # Communication infrastructure
        self.message_queue = queue.PriorityQueue()
        self.response_waiters = {}
        self.active_sessions = {}
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.running = False
        self.background_threads = []
        
        # Message statistics
        self.stats = CommunicationStats(
            total_messages_sent=0,
            total_messages_received=0,
            messages_by_type={message_type: 0 for message_type in MessageType},
            average_response_time=0.0,
            active_connections=0,
            memory_shares_active=0,
            coordination_requests_active=0
        )
        
        # Setup message handlers
        self._setup_message_handlers()
    
    def start(self):
        """Start the communication system"""
        self.running = True
        
        # Start background threads
        message_worker_thread = threading.Thread(target=self._message_worker, daemon=True)
        message_worker_thread.start()
        self.background_threads.append(message_worker_thread)
        
        heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        heartbeat_thread.start()
        self.background_threads.append(heartbeat_thread)
        
        cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        cleanup_thread.start()
        self.background_threads.append(cleanup_thread)
        
        logger.info("Multi-agent communication system started")
    
    def stop(self):
        """Stop the communication system"""
        self.running = False
        
        # Wait for threads to finish
        for thread in self.background_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        logger.info("Multi-agent communication system stopped")
    
    def register_agent(self, agent_id: str, role: AgentRole, capabilities: List[str] = None):
        """Register an agent for communication"""
        
        if not capabilities:
            # Default capabilities based on role
            role_capabilities = {
                AgentRole.STRATEGIST: ["strategy", "pattern_analysis", "performance_optimization"],
                AgentRole.ANALYST: ["market_analysis", "data_processing", "trend_detection"],
                AgentRole.RISK_MANAGER: ["risk_assessment", "risk_management", "alert_generation"],
                AgentRole.COORDINATOR: ["coordination", "orchestration", "communication"],
                AgentRole.SPECIST: ["specialization", "expertise", "consultation"],
                AgentRole.OBSERVER: ["monitoring", "observation", "data_collection"]
            }
            capabilities = role_capabilities.get(role, [])
        
        self.agent_registry.register_agent(agent_id, role, capabilities)
        
        # Send registration message
        self.send_status_update(
            sender_agent_id=agent_id,
            status="registered",
            metadata={"role": role.value, "capabilities": capabilities}
        )
    
    def send_direct_message(self,
                          sender_agent_id: str,
                          receiver_agent_id: str,
                          subject: str,
                          content: str,
                          priority: CommunicationPriority = CommunicationPriority.NORMAL,
                          attachments: List[Dict[str, Any]] = None) -> str:
        """Send direct message to specific agent"""
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=sender_agent_id,
            receiver_agent_id=receiver_agent_id,
            message_type=MessageType.DIRECT_MESSAGE,
            priority=priority,
            subject=subject,
            content=content,
            attachments=attachments or [],
            timestamp=datetime.now(),
            expires_at=None,
            correlation_id=None,
            reply_to=None,
            metadata={}
        )
        
        return self._send_message(message)
    
    def broadcast_message(self,
                         sender_agent_id: str,
                         subject: str,
                         content: str,
                         priority: CommunicationPriority = CommunicationPriority.NORMAL,
                         target_roles: List[AgentRole] = None,
                         attachments: List[Dict[str, Any]] = None) -> List[str]:
        """Broadcast message to multiple agents"""
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=sender_agent_id,
            receiver_agent_id=None,
            message_type=MessageType.BROADCAST,
            priority=priority,
            subject=subject,
            content=content,
            attachments=attachments or [],
            timestamp=datetime.now(),
            expires_at=None,
            correlation_id=None,
            reply_to=None,
            metadata={"target_roles": [role.value for role in target_roles] if target_roles else []}
        )
        
        recipients = self._send_message(message)
        return recipients
    
    def share_memory(self,
                    sharing_agent_id: str,
                    recipient_agent_id: str,
                    memory_block_ids: List[str],
                    access_level: str = "read",
                    duration: timedelta = timedelta(hours=24),
                    conditions: Dict[str, Any] = None) -> str:
        """Share memory blocks between agents"""
        
        # Create memory share request
        memory_share = MemoryShare(
            memory_block_ids=memory_block_ids,
            access_level=access_level,
            duration=duration,
            sharing_agent_id=sharing_agent_id,
            recipient_agent_id=recipient_agent_id,
            conditions=conditions or {}
        )
        
        # Create message
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=sharing_agent_id,
            receiver_agent_id=recipient_agent_id,
            message_type=MessageType.MEMORY_SHARE,
            priority=CommunicationPriority.NORMAL,
            subject=f"Memory Share: {len(memory_block_ids)} blocks",
            content=f"Sharing {len(memory_block_ids)} memory blocks with {access_level} access",
            attachments=[],
            timestamp=datetime.now(),
            expires_at=datetime.now() + duration,
            correlation_id=None,
            reply_to=None,
            metadata={
                "memory_share": asdict(memory_share),
                "access_level": access_level,
                "duration": duration.total_seconds()
            }
        )
        
        return self._send_message(message)
    
    def request_coordination(self,
                           requesting_agent: str,
                           target_agents: List[str],
                           coordination_type: str,
                           parameters: Dict[str, Any],
                           deadline: timedelta = timedelta(hours=1),
                           required_responses: int = None) -> str:
        """Request coordination between agents"""
        
        if required_responses is None:
            required_responses = len(target_agents)
        
        coordination_request = CoordinationRequest(
            request_id=str(uuid.uuid4()),
            requesting_agent=requesting_agent,
            target_agents=target_agents,
            coordination_type=coordination_type,
            parameters=parameters,
            deadline=datetime.now() + deadline,
            required_responses=required_responses
        )
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=requesting_agent,
            receiver_agent_id=None,
            message_type=MessageType.COORDINATION_REQUEST,
            priority=CommunicationPriority.HIGH,
            subject=f"Coordination Request: {coordination_type}",
            content=f"Requesting {coordination_type} coordination from {len(target_agents)} agents",
            attachments=[],
            timestamp=datetime.now(),
            expires_at=datetime.now() + deadline,
            correlation_id=coordination_request.request_id,
            reply_to=None,
            metadata={
                "coordination_request": asdict(coordination_request)
            }
        )
        
        # Send to all target agents
        recipients = []
        for target_agent in target_agents:
            message.receiver_agent_id = target_agent
            recipient = self._send_message(message)
            recipients.extend(recipient)
        
        return coordination_request.request_id
    
    def send_strategy_request(self,
                            sender_agent_id: str,
                            target_agents: List[str],
                            query: str,
                            context: Dict[str, Any] = None) -> str:
        """Request strategy advice from agents"""
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=sender_agent_id,
            receiver_agent_id=None,
            message_type=MessageType.STRATEGY_REQUEST,
            priority=CommunicationPriority.NORMAL,
            subject=f"Strategy Request: {query[:50]}...",
            content=query,
            attachments=[],
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=2),
            correlation_id=None,
            reply_to=None,
            metadata={
                "query": query,
                "context": context or {},
                "requesting_agent": sender_agent_id
            }
        )
        
        # Send to all target agents
        recipients = []
        for target_agent in target_agents:
            message.receiver_agent_id = target_agent
            recipient = self._send_message(message)
            recipients.extend(recipient)
        
        return message.message_id
    
    def send_performance_update(self,
                              agent_id: str,
                              performance_data: Dict[str, Any],
                              recipients: List[str] = None) -> str:
        """Send performance update to other agents"""
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=agent_id,
            receiver_agent_id=None,
            message_type=MessageType.PERFORMANCE_UPDATE,
            priority=CommunicationPriority.NORMAL,
            subject=f"Performance Update: {performance_data.get('metric', 'General')}",
            content=f"Performance metrics: {json.dumps(performance_data, indent=2)}",
            attachments=[],
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
            correlation_id=None,
            reply_to=None,
            metadata={
                "performance_data": performance_data,
                "update_type": "metrics"
            }
        )
        
        if recipients:
            # Send to specific recipients
            for recipient in recipients:
                message.receiver_agent_id = recipient
                self._send_message(message)
        else:
            # Broadcast to all active agents
            self.broadcast_message(
                sender_agent_id=agent_id,
                subject=message.subject,
                content=message.content,
                priority=message.priority,
                attachments=message.attachments
            )
        
        return message.message_id
    
    def send_risk_alert(self,
                      agent_id: str,
                      risk_level: str,
                      description: str,
                      risk_data: Dict[str, Any],
                      target_agents: List[str] = None) -> str:
        """Send risk alert to appropriate agents"""
        
        priority = CommunicationPriority.CRITICAL if risk_level == "high" else CommunicationPriority.HIGH
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=agent_id,
            receiver_agent_id=None,
            message_type=MessageType.RISK_ALERT,
            priority=priority,
            subject=f"Risk Alert ({risk_level.upper()}): {description[:50]}...",
            content=f"Risk Alert Details:\n\n{risk_data}",
            attachments=[],
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(days=1),
            correlation_id=None,
            reply_to=None,
            metadata={
                "risk_level": risk_level,
                "description": description,
                "risk_data": risk_data,
                "alert_timestamp": datetime.now().isoformat()
            }
        )
        
        if target_agents:
            # Send to specific agents
            for target_agent in target_agents:
                message.receiver_agent_id = target_agent
                self._send_message(message)
        else:
            # Auto-route to risk managers and coordinators
            self._send_message(message)
        
        return message.message_id
    
    def send_learning_update(self,
                           agent_id: str,
                           learning_data: Dict[str, Any],
                           target_agents: List[str] = None) -> str:
        """Send learning update to other agents"""
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=agent_id,
            receiver_agent_id=None,
            message_type=MessageType.LEARNING_UPDATE,
            priority=CommunicationPriority.NORMAL,
            subject=f"Learning Update: {learning_data.get('learning_type', 'General')}",
            content=f"New learning insights:\n\n{json.dumps(learning_data, indent=2)}",
            attachments=[],
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(days=3),
            correlation_id=None,
            reply_to=None,
            metadata={
                "learning_data": learning_data,
                "learning_type": learning_data.get("learning_type", "general")
            }
        )
        
        if target_agents:
            for target_agent in target_agents:
                message.receiver_agent_id = target_agent
                self._send_message(message)
        else:
            # Broadcast to strategists and analysts
            strategists = self.agent_registry.get_active_agents(AgentRole.STRATEGIST)
            analysts = self.agent_registry.get_active_agents(AgentRole.ANALYST)
            target_agents = strategists + analysts
            
            for target_agent in target_agents:
                if target_agent != agent_id:  # Don't send to self
                    message.receiver_agent_id = target_agent
                    self._send_message(message)
        
        return message.message_id
    
    def send_status_update(self,
                         sender_agent_id: str,
                         status: str,
                         metadata: Dict[str, Any] = None) -> str:
        """Send status update to coordinator agents"""
        
        coordinators = self.agent_registry.get_active_agents(AgentRole.COORDINATOR)
        
        if not coordinators:
            # If no coordinators, broadcast to all agents
            return self.broadcast_message(
                sender_agent_id=sender_agent_id,
                subject=f"Status Update: {status}",
                content=f"Agent {sender_agent_id} status: {status}",
                metadata=metadata or {}
            )
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=sender_agent_id,
            receiver_agent_id=None,
            message_type=MessageType.STATUS_UPDATE,
            priority=CommunicationPriority.NORMAL,
            subject=f"Status Update: {status}",
            content=f"Agent {sender_agent_id} has updated status to: {status}",
            attachments=[],
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            correlation_id=None,
            reply_to=None,
            metadata=metadata or {}
        )
        
        for coordinator in coordinators:
            if coordinator != sender_agent_id:  # Don't send to self
                message.receiver_agent_id = coordinator
                self._send_message(message)
        
        return message.message_id
    
    def respond_to_message(self,
                         message_id: str,
                         responder_agent_id: str,
                         response_content: str,
                         attachments: List[Dict[str, Any]] = None) -> str:
        """Respond to a received message"""
        
        # Find the original message
        original_message = self._find_message(message_id)
        if not original_message:
            logger.warning(f"Original message {message_id} not found for response")
            return None
        
        response_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=responder_agent_id,
            receiver_agent_id=original_message.sender_agent_id,
            message_type=MessageType.DIRECT_MESSAGE,
            priority=original_message.priority,
            subject=f"Re: {original_message.subject}",
            content=response_content,
            attachments=attachments or [],
            timestamp=datetime.now(),
            expires_at=None,
            correlation_id=original_message.correlation_id,
            reply_to=message_id,
            metadata={
                "response_to": message_id,
                "original_sender": original_message.sender_agent_id
            }
        )
        
        return self._send_message(response_message)
    
    def get_communication_stats(self) -> CommunicationStats:
        """Get communication statistics"""
        return self.stats
    
    def get_message_history(self, 
                          agent_id: str = None,
                          message_type: MessageType = None,
                          time_range: timedelta = None) -> List[Dict[str, Any]]:
        """Get message history with filters"""
        
        history = self.message_router.message_history.copy()
        
        # Apply filters
        if agent_id:
            history = [msg for msg in history if msg["sender"] == agent_id]
        
        if message_type:
            history = [msg for msg in history if msg["type"] == message_type.value]
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            history = [msg for msg in history if msg["timestamp"] >= cutoff_time]
        
        return history
    
    def cleanup_agent_session(self, agent_id: str):
        """Cleanup when agent disconnects"""
        
        # Remove from registry
        self.agent_registry.unregister_agent(agent_id)
        
        # Cancel any pending responses
        if agent_id in self.response_waiters:
            del self.response_waiters[agent_id]
        
        # Clear active sessions
        sessions_to_clear = [session_id for session_id, session in self.active_sessions.items() 
                           if session.get("agent_id") == agent_id]
        
        for session_id in sessions_to_clear:
            del self.active_sessions[session_id]
        
        logger.info(f"Cleaned up session for agent {agent_id}")
    
    # Internal methods
    
    def _setup_message_handlers(self):
        """Setup message handlers for different message types"""
        
        # Memory share handler
        def handle_memory_share(message: AgentMessage, recipients: List[str]):
            memory_share_data = message.metadata.get("memory_share")
            if memory_share_data:
                memory_share = MemoryShare(**memory_share_data)
                
                # Process memory sharing
                self._process_memory_share(message, memory_share)
        
        # Strategy request handler
        def handle_strategy_request(message: AgentMessage, recipients: List[str]):
            # Find agents capable of strategy responses
            for recipient in recipients:
                if recipient != message.sender_agent_id:
                    # Send strategy response request
                    self._send_strategy_response_request(message, recipient)
        
        # Coordination request handler
        def handle_coordination_request(message: AgentMessage, recipients: List[str]):
            coordination_data = message.metadata.get("coordination_request")
            if coordination_data:
                self._process_coordination_request(message, CoordinationRequest(**coordination_data))
        
        # Risk alert handler
        def handle_risk_alert(message: AgentMessage, recipients: List[str]):
            logger.warning(f"Risk alert received from {message.sender_agent_id}: {message.subject}")
            # Could trigger additional risk management processes
        
        # Register handlers
        self.message_router.register_handler(MessageType.MEMORY_SHARE, handle_memory_share)
        self.message_router.register_handler(MessageType.STRATEGY_REQUEST, handle_strategy_request)
        self.message_router.register_handler(MessageType.COORDINATION_REQUEST, handle_coordination_request)
        self.message_router.register_handler(MessageType.RISK_ALERT, handle_risk_alert)
    
    def _send_message(self, message: AgentMessage) -> List[str]:
        """Internal message sending"""
        
        # Route message
        recipients = self.message_router.route_message(message)
        
        # Add to queue for processing
        priority_value = 100 - message.priority.value  # Invert for priority queue (lower number = higher priority)
        self.message_queue.put((priority_value, message.timestamp.timestamp(), message, recipients))
        
        # Update statistics
        self.stats.total_messages_sent += 1
        self.stats.messages_by_type[message.message_type] = self.stats.messages_by_type.get(message.message_type, 0) + 1
        self.stats.active_connections = len(self.agent_registry.get_active_agents())
        
        logger.info(f"Sent message {message.message_id} from {message.sender_agent_id} to {recipients}")
        
        return recipients
    
    def _message_worker(self):
        """Background worker for processing message queue"""
        
        while self.running:
            try:
                if not self.message_queue.empty():
                    _, _, message, recipients = self.message_queue.get_nowait()
                    
                    # Process message for each recipient
                    for recipient in recipients:
                        self._deliver_message(message, recipient)
                    
                    # Update statistics
                    self.stats.total_messages_received += len(recipients)
                
                threading.Event().wait(0.1)  # Prevent busy waiting
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Message worker error: {e}")
                threading.Event().wait(1)
    
    def _deliver_message(self, message: AgentMessage, recipient: str):
        """Deliver message to recipient agent"""
        
        try:
            # Update agent heartbeat
            self.agent_registry.update_agent_heartbeat(recipient)
            
            # Deliver via Letta API
            delivery_result = self._deliver_via_letta(message, recipient)
            
            if delivery_result.get("success"):
                logger.debug(f"Message {message.message_id} delivered to {recipient}")
            else:
                logger.warning(f"Failed to deliver message {message.message_id} to {recipient}: {delivery_result.get('error')}")
                
        except Exception as e:
            logger.error(f"Error delivering message to {recipient}: {e}")
    
    def _deliver_via_letta(self, message: AgentMessage, recipient: str) -> Dict[str, Any]:
        """Deliver message via Letta REST API"""
        
        try:
            # Format message for Letta
            letta_message = {
                "message": f"[{message.message_type.value}] {message.subject}\n\n{message.content}",
                "role": "assistant",
                "stream": False
            }
            
            # Send via Letta client
            result = self.letta_client.send_message(recipient, letta_message["message"])
            
            return {"success": True, "result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _find_message(self, message_id: str) -> Optional[AgentMessage]:
        """Find message by ID in history"""
        for msg_data in self.message_router.message_history:
            if msg_data["message_id"] == message_id:
                # This is a simplified version - in practice, you'd store full message objects
                return None  # Would reconstruct full message object
        return None
    
    def _process_memory_share(self, message: AgentMessage, memory_share: MemoryShare):
        """Process memory sharing between agents"""
        
        try:
            # Share each memory block
            shared_blocks = []
            for block_id in memory_share.memory_block_ids:
                # Get memory block from sharing agent
                memory_block = self.memory_manager.get_memory_block(
                    memory_share.sharing_agent_id, 
                    block_id
                )
                
                if memory_block:
                    # Create copy for recipient
                    shared_block_data = memory_block.to_dict()
                    shared_block_data["metadata"]["source_agent"] = memory_share.sharing_agent_id
                    shared_block_data["metadata"]["shared_by"] = message.sender_agent_id
                    shared_block_data["metadata"]["share_timestamp"] = datetime.now().isoformat()
                    shared_block_data["metadata"]["access_level"] = memory_share.access_level
                    
                    # Add to recipient's memory (or create new block)
                    if memory_share.access_level == "read":
                        # Add as reference in recipient's memory
                        reference_block = {
                            "block_type": "memory_reference",
                            "title": f"Shared: {memory_block.title}",
                            "content": f"Memory block shared from {memory_share.sharing_agent_id}: {memory_block.title}",
                            "metadata": {
                                "reference_to": block_id,
                                "source_agent": memory_share.sharing_agent_id,
                                "shared_by": message.sender_agent_id,
                                "share_timestamp": datetime.now().isoformat()
                            }
                        }
                        
                        # Store reference in recipient's memory
                        self.memory_manager.create_memory_block(
                            memory_share.recipient_agent_id,
                            MemoryBlockType.SYSTEM_CONTEXT,
                            reference_block["title"],
                            reference_block["content"],
                            metadata_updates=reference_block["metadata"]
                        )
                    
                    shared_blocks.append(block_id)
            
            # Update statistics
            self.stats.memory_shares_active += 1
            
            # Send confirmation to sender
            if shared_blocks:
                self.send_direct_message(
                    recipient_agent_id=message.sender_agent_id,
                    sender_agent_id="system",
                    subject="Memory Share Completed",
                    content=f"Successfully shared {len(shared_blocks)} memory blocks to {memory_share.recipient_agent_id}"
                )
            
            logger.info(f"Memory share completed: {len(shared_blocks)} blocks shared from {memory_share.sharing_agent_id} to {memory_share.recipient_agent_id}")
            
        except Exception as e:
            logger.error(f"Error processing memory share: {e}")
    
    def _send_strategy_response_request(self, original_message: AgentMessage, recipient: str):
        """Send strategy response request to agent"""
        
        query = original_message.metadata.get("query", "")
        context = original_message.metadata.get("context", {})
        
        response_message = f"""
Strategy Request from {original_message.sender_agent_id}:

Query: {query}

Context: {json.dumps(context, indent=2)}

Please provide your strategic advice based on your memory and capabilities.
"""
        
        self.send_direct_message(
            sender_agent_id="system",
            receiver_agent_id=recipient,
            subject=f"Strategy Response Request: {original_message.subject}",
            content=response_message,
            priority=CommunicationPriority.NORMAL
        )
    
    def _process_coordination_request(self, message: AgentMessage, coordination_request: CoordinationRequest):
        """Process coordination request between agents"""
        
        try:
            # Log coordination request
            logger.info(f"Processing coordination request {coordination_request.request_id} from {coordination_request.requesting_agent}")
            
            # Send coordination instructions to target agents
            for target_agent in coordination_request.target_agents:
                if target_agent != coordination_request.requesting_agent:
                    self.send_direct_message(
                        sender_agent_id="system",
                        receiver_agent_id=target_agent,
                        subject=f"Coordination Request: {coordination_request.coordination_type}",
                        content=f"""
Coordination request from {coordination_request.requesting_agent}:

Type: {coordination_request.coordination_type}
Parameters: {json.dumps(coordination_request.parameters, indent=2)}
Deadline: {coordination_request.deadline.isoformat()}

Please respond with your coordination status and any relevant information.
""",
                        priority=CommunicationPriority.HIGH
                    )
            
            self.stats.coordination_requests_active += 1
            
        except Exception as e:
            logger.error(f"Error processing coordination request: {e}")
    
    def _heartbeat_worker(self):
        """Background worker for agent heartbeat monitoring"""
        
        while self.running:
            try:
                # Update registry heartbeat
                current_time = datetime.now()
                active_agents = self.agent_registry.get_active_agents()
                
                for agent_id in active_agents:
                    self.agent_registry.update_agent_heartbeat(agent_id)
                
                # Send periodic status updates
                if active_agents:
                    # Send status to coordinators
                    coordinators = self.agent_registry.get_active_agents(AgentRole.COORDINATOR)
                    for coordinator in coordinators:
                        self.send_status_update(
                            sender_agent_id="system",
                            status="heartbeat",
                            metadata={
                                "active_agents": len(active_agents),
                                "timestamp": current_time.isoformat()
                            }
                        )
                
                # Wait 30 seconds before next heartbeat
                for _ in range(30):
                    if not self.running:
                        break
                    threading.Event().wait(1)
                
            except Exception as e:
                logger.error(f"Heartbeat worker error: {e}")
                threading.Event().wait(30)
    
    def _cleanup_worker(self):
        """Background worker for cleanup tasks"""
        
        while self.running:
            try:
                # Clean up expired messages
                current_time = datetime.now()
                
                # This would iterate through message queue and remove expired messages
                # Implementation depends on specific requirements
                
                # Clean up old message history
                if len(self.message_router.message_history) > 2000:
                    self.message_router.message_history = self.message_router.message_history[-1000:]
                
                # Clean up old coordination requests
                # Implementation for coordination request cleanup
                
                # Wait 5 minutes before next cleanup
                for _ in range(300):
                    if not self.running:
                        break
                    threading.Event().wait(1)
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                threading.Event().wait(300)