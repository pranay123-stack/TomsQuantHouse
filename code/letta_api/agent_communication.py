#!/usr/bin/env python3
"""
Agent Communication and Coordination Module for Letta API

Provides advanced multi-agent communication, coordination capabilities,
memory sharing, and intelligent message routing for agent ecosystems.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import uuid
import hashlib
import time

from letta_client import LettaAPIClient, AgentRole, Priority

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages between agents"""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    COORDINATION_REQUEST = "coordination_request"
    RISK_ALERT = "risk_alert"
    PERFORMANCE_UPDATE = "performance_update"
    MEMORY_SHARE = "memory_share"
    COLLABORATION = "collaboration"
    STATUS_UPDATE = "status_update"


class MessagePriority(Enum):
    """Message priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class CoordinationType(Enum):
    """Types of agent coordination"""
    TRADE_EXECUTION = "trade_execution"
    RISK_MANAGEMENT = "risk_management"
    STRATEGY_DEVELOPMENT = "strategy_development"
    MARKET_ANALYSIS = "market_analysis"
    PERFORMANCE_REVIEW = "performance_review"
    EMERGENCY_RESPONSE = "emergency_response"


class AccessLevel(Enum):
    """Memory access levels for sharing"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    TEMPORARY_ACCESS = "temporary_access"
    COLLABORATIVE_EDIT = "collaborative_edit"


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    description: str
    level: int  # 1-5 skill level
    tags: List[str]
    last_demonstrated: Optional[datetime] = None
    success_rate: float = 0.0


@dataclass
class AgentRegistration:
    """Agent registration information"""
    agent_id: str
    name: str
    role: AgentRole
    capabilities: List[AgentCapability]
    contact_info: Dict[str, Any]
    availability: str
    status: str
    registered_at: datetime
    last_seen: datetime
    performance_score: float = 0.0
    active_collaborations: List[str] = None


@dataclass
class InterAgentMessage:
    """Inter-agent message structure"""
    message_id: str
    sender_agent_id: str
    receiver_agent_id: str
    subject: str
    content: str
    message_type: MessageType
    priority: MessagePriority
    timestamp: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class MemoryShare:
    """Memory sharing configuration"""
    share_id: str
    sharing_agent_id: str
    recipient_agent_id: str
    memory_block_ids: List[str]
    access_level: AccessLevel
    duration_hours: int
    created_at: datetime
    expires_at: datetime
    access_log: List[Dict[str, Any]] = None


@dataclass
class CoordinationRequest:
    """Agent coordination request"""
    request_id: str
    requesting_agent_id: str
    coordination_type: CoordinationType
    description: str
    required_capabilities: List[str]
    participants: List[str]
    priority: MessagePriority
    deadline: Optional[datetime] = None
    status: str = "pending"
    created_at: datetime = None
    responses: List[Dict[str, Any]] = None


@dataclass
class RiskAlert:
    """Risk alert message"""
    alert_id: str
    source_agent_id: str
    risk_level: str
    description: str
    affected_agents: List[str]
    risk_data: Dict[str, Any]
    mitigation_actions: List[str]
    timestamp: datetime
    acknowledged_by: List[str] = None


class AgentCommunicationHub:
    """
    Advanced Agent Communication Hub
    
    Provides comprehensive multi-agent communication capabilities including:
    - Agent registration and capability tracking
    - Intelligent message routing
    - Memory sharing between agents
    - Coordination request handling
    - Risk alert distribution
    - Performance update broadcasting
    - Communication analytics and monitoring
    """
    
    def __init__(self, client: LettaAPIClient):
        self.client = client
        self.agent_registry = {}  # In-memory registry (in production, use database)
        self.message_history = deque(maxlen=10000)
        self.memory_shares = {}
        self.coordination_requests = {}
        self.active_collaborations = {}
        
    # === AGENT REGISTRY MANAGEMENT ===
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        role: AgentRole,
        capabilities: List[AgentCapability],
        contact_info: Dict[str, Any] = None
    ) -> bool:
        """
        Register an agent in the communication hub
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable agent name
            role: Agent's primary role
            capabilities: List of agent capabilities
            contact_info: Additional contact information
        """
        
        registration = AgentRegistration(
            agent_id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities,
            contact_info=contact_info or {},
            availability="available",
            status="active",
            registered_at=datetime.now(),
            last_seen=datetime.now(),
            performance_score=0.0,
            active_collaborations=[]
        )
        
        self.agent_registry[agent_id] = registration
        
        # Also create a memory block to persist registration info
        registration_data = asdict(registration)
        registration_block_id = self.client.add_memory_block(
            agent_id=agent_id,
            block_type=MemoryBlockType.SYSTEM_CONTEXT,
            title=f"Agent Registration - {name}",
            content=json.dumps(registration_data, indent=2),
            metadata={
                "registration_type": "agent_communication",
                "registered_by": "communication_hub",
                "role": role.value
            },
            tags=["registration", role.value, "communication"],
            priority=Priority.HIGH
        )
        
        logger.info(f"Agent registered: {name} ({agent_id}) with {len(capabilities)} capabilities")
        return True
    
    def update_agent_status(
        self,
        agent_id: str,
        status: str,
        availability: str = None,
        performance_score: float = None
    ) -> bool:
        """Update agent status and availability"""
        
        if agent_id not in self.agent_registry:
            logger.error(f"Agent not registered: {agent_id}")
            return False
        
        registration = self.agent_registry[agent_id]
        registration.status = status
        registration.last_seen = datetime.now()
        
        if availability is not None:
            registration.availability = availability
        if performance_score is not None:
            registration.performance_score = performance_score
        
        # Broadcast status update to relevant agents
        status_update = InterAgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id="communication_hub",
            receiver_agent_id="",  # Will be set during broadcast
            subject=f"Agent Status Update: {registration.name}",
            content=f"Agent {registration.name} is now {status}",
            message_type=MessageType.STATUS_UPDATE,
            priority=MessagePriority.NORMAL,
            timestamp=datetime.now(),
            metadata={
                "agent_id": agent_id,
                "new_status": status,
                "availability": registration.availability
            }
        )
        
        # Only broadcast to active agents
        active_agents = [aid for aid, reg in self.agent_registry.items() 
                        if reg.status == "active" and aid != agent_id]
        
        for target_agent_id in active_agents:
            status_update.receiver_agent_id = target_agent_id
            self._deliver_message(status_update)
        
        return True
    
    def get_registered_agents(self, role_filter: Optional[AgentRole] = None) -> List[AgentRegistration]:
        """Get list of registered agents, optionally filtered by role"""
        
        agents = list(self.agent_registry.values())
        
        if role_filter:
            agents = [agent for agent in agents if agent.role == role_filter]
        
        return sorted(agents, key=lambda x: x.performance_score, reverse=True)
    
    def find_agent_by_capability(
        self,
        capability_name: str,
        min_level: int = 3,
        available_only: bool = True
    ) -> List[AgentRegistration]:
        """Find agents with specific capability"""
        
        matching_agents = []
        
        for registration in self.agent_registry.values():
            # Skip if agent is not available and filter is set
            if available_only and registration.availability != "available":
                continue
            
            # Check capabilities
            for capability in registration.capabilities:
                if (capability.name == capability_name and 
                    capability.level >= min_level):
                    matching_agents.append(registration)
                    break
        
        return sorted(matching_agents, key=lambda x: x.performance_score, reverse=True)
    
    # === MESSAGE ROUTING AND DELIVERY ===
    
    def send_direct_message(
        self,
        sender_agent_id: str,
        receiver_agent_id: str,
        subject: str,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        message_type: MessageType = MessageType.DIRECT,
        metadata: Dict[str, Any] = None,
        expires_in_hours: Optional[int] = None
    ) -> Optional[str]:
        """Send direct message between agents"""
        
        # Validate sender and receiver exist
        if sender_agent_id not in self.agent_registry:
            logger.error(f"Sender agent not registered: {sender_agent_id}")
            return None
        
        if receiver_agent_id not in self.agent_registry:
            logger.error(f"Receiver agent not registered: {receiver_agent_id}")
            return None
        
        # Create message
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        message = InterAgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent_id=sender_agent_id,
            receiver_agent_id=receiver_agent_id,
            subject=subject,
            content=content,
            message_type=message_type,
            priority=priority,
            timestamp=datetime.now(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # Deliver message
        success = self._deliver_message(message)
        
        if success:
            logger.info(f"Direct message sent: {sender_agent_id} -> {receiver_agent_id}: {subject[:50]}")
            return message.message_id
        else:
            logger.error(f"Failed to deliver message: {message_id}")
            return None
    
    def broadcast_message(
        self,
        sender_agent_id: str,
        subject: str,
        content: str,
        target_roles: List[AgentRole] = None,
        target_agents: List[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        exclude_sender: bool = True
    ) -> List[str]:
        """Broadcast message to multiple agents"""
        
        if sender_agent_id not in self.agent_registry:
            logger.error(f"Sender agent not registered: {sender_agent_id}")
            return []
        
        # Determine target agents
        if target_agents:
            target_agent_list = target_agents
        elif target_roles:
            target_agent_list = [
                agent.agent_id for agent in self.get_registered_agents()
                if agent.role in target_roles and agent.status == "active"
            ]
        else:
            # Broadcast to all active agents
            target_agent_list = [
                agent.agent_id for agent in self.get_registered_agents()
                if agent.status == "active"
            ]
        
        # Exclude sender if requested
        if exclude_sender:
            target_agent_list = [aid for aid in target_agent_list if aid != sender_agent_id]
        
        # Send messages
        message_ids = []
        for target_agent_id in target_agent_list:
            message_id = self.send_direct_message(
                sender_agent_id=sender_agent_id,
                receiver_agent_id=target_agent_id,
                subject=subject,
                content=content,
                priority=priority,
                message_type=MessageType.BROADCAST
            )
            if message_id:
                message_ids.append(message_id)
        
        logger.info(f"Broadcast message sent by {sender_agent_id} to {len(message_ids)} agents")
        return message_ids
    
    def route_intelligent_message(
        self,
        sender_agent_id: str,
        content: str,
        context: Dict[str, Any] = None,
        auto_route: bool = True
    ) -> Optional[str]:
        """Intelligently route message based on content analysis"""
        
        if not auto_route:
            # Manual routing - return the content for manual processing
            return content
        
        # Analyze content for routing hints
        content_lower = content.lower()
        context = context or {}
        
        # Risk-related messages
        if any(word in content_lower for word in ['risk', 'alert', 'volatility', 'drawdown']):
            risk_agents = self.find_agent_by_capability("risk_management")
            if risk_agents:
                target_agent = risk_agents[0]
                return self.send_direct_message(
                    sender_agent_id=sender_agent_id,
                    receiver_agent_id=target_agent.agent_id,
                    subject="Risk Alert from Intelligent Routing",
                    content=content,
                    priority=MessagePriority.HIGH,
                    message_type=MessageType.RISK_ALERT,
                    metadata=context
                )
        
        # Trading strategy messages
        elif any(word in content_lower for word in ['strategy', 'pattern', 'setup', 'signal']):
            strategist_agents = self.find_agent_by_capability("strategy_development")
            if strategist_agents:
                target_agent = strategist_agents[0]
                return self.send_direct_message(
                    sender_agent_id=sender_agent_id,
                    receiver_agent_id=target_agent.agent_id,
                    subject="Strategy Consultation Request",
                    content=content,
                    priority=MessagePriority.NORMAL,
                    message_type=MessageType.DIRECT,
                    metadata=context
                )
        
        # Market analysis messages
        elif any(word in content_lower for word in ['market', 'analysis', 'trend', 'regime']):
            analyst_agents = self.find_agent_by_capability("market_analysis")
            if analyst_agents:
                target_agent = analyst_agents[0]
                return self.send_direct_message(
                    sender_agent_id=sender_agent_id,
                    receiver_agent_id=target_agent.agent_id,
                    subject="Market Analysis Request",
                    content=content,
                    priority=MessagePriority.NORMAL,
                    message_type=MessageType.DIRECT,
                    metadata=context
                )
        
        # Default routing - send to coordinator if available
        coordinator_agents = self.get_registered_agents(role_filter=AgentRole.COORDINATOR)
        if coordinator_agents:
            target_agent = coordinator_agents[0]
            return self.send_direct_message(
                sender_agent_id=sender_agent_id,
                receiver_agent_id=target_agent.agent_id,
                subject="General Message (Auto-routed)",
                content=content,
                priority=MessagePriority.NORMAL,
                message_type=MessageType.DIRECT,
                metadata=context
            )
        
        # No suitable agent found
        logger.warning(f"No suitable agent found for intelligent routing: {content[:50]}")
        return None
    
    def _deliver_message(self, message: InterAgentMessage) -> bool:
        """Deliver message to target agent"""
        
        try:
            # Store message in history
            self.message_history.append(message)
            
            # Send via Letta API
            response = self.client.send_message(
                sender_agent_id=message.sender_agent_id,
                receiver_agent_id=message.receiver_agent_id,
                subject=message.subject,
                content=message.content,
                priority=message.priority.value,
                message_type=message.message_type.value
            )
            
            # Update agent last seen times
            if message.sender_agent_id in self.agent_registry:
                self.agent_registry[message.sender_agent_id].last_seen = datetime.now()
            
            return "error" not in response
            
        except Exception as e:
            logger.error(f"Failed to deliver message {message.message_id}: {e}")
            return False
    
    def get_agent_messages(
        self,
        agent_id: str,
        message_type: Optional[MessageType] = None,
        limit: int = 50,
        include_sent: bool = True
    ) -> List[InterAgentMessage]:
        """Get messages for an agent"""
        
        messages = []
        
        # Get messages from history
        for message in reversed(self.message_history):
            # Check if agent is sender or receiver
            is_relevant = (
                message.receiver_agent_id == agent_id or
                (include_sent and message.sender_agent_id == agent_id)
            )
            
            if not is_relevant:
                continue
            
            # Filter by message type if specified
            if message_type and message.message_type != message_type:
                continue
            
            # Check if message has expired
            if message.expires_at and datetime.now() > message.expires_at:
                continue
            
            messages.append(message)
            
            if len(messages) >= limit:
                break
        
        return messages
    
    # === MEMORY SHARING ===
    
    def share_memory_blocks(
        self,
        sharing_agent_id: str,
        recipient_agent_id: str,
        memory_block_ids: List[str],
        access_level: AccessLevel,
        duration_hours: int = 24,
        description: str = ""
    ) -> Optional[str]:
        """Share memory blocks between agents"""
        
        # Validate both agents exist
        if sharing_agent_id not in self.agent_registry:
            logger.error(f"Sharing agent not registered: {sharing_agent_id}")
            return None
        
        if recipient_agent_id not in self.agent_registry:
            logger.error(f"Recipient agent not registered: {recipient_agent_id}")
            return None
        
        # Create share record
        share_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        memory_share = MemoryShare(
            share_id=share_id,
            sharing_agent_id=sharing_agent_id,
            recipient_agent_id=recipient_agent_id,
            memory_block_ids=memory_block_ids,
            access_level=access_level,
            duration_hours=duration_hours,
            created_at=datetime.now(),
            expires_at=expires_at,
            access_log=[]
        )
        
        self.memory_shares[share_id] = memory_share
        
        # Send notification to recipient
        notification = self.send_direct_message(
            sender_agent_id="communication_hub",
            receiver_agent_id=recipient_agent_id,
            subject="Memory Sharing Notification",
            content=f"Agent {sharing_agent_id} has shared {len(memory_block_ids)} memory blocks with you. "
                   f"Access level: {access_level.value}, Duration: {duration_hours} hours. "
                   f"Share ID: {share_id}",
            priority=MessagePriority.NORMAL,
            message_type=MessageType.MEMORY_SHARE,
            metadata={
                "share_id": share_id,
                "sharing_agent_id": sharing_agent_id,
                "access_level": access_level.value,
                "expires_at": expires_at.isoformat()
            }
        )
        
        logger.info(f"Memory shared: {sharing_agent_id} -> {recipient_agent_id} ({len(memory_block_ids)} blocks)")
        return share_id
    
    def get_shared_memory(
        self,
        recipient_agent_id: str,
        access_level: AccessLevel = AccessLevel.READ_ONLY
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get memory blocks shared with an agent"""
        
        accessible_shares = []
        current_time = datetime.now()
        
        # Find valid shares
        for share in self.memory_shares.values():
            if (share.recipient_agent_id == recipient_agent_id and 
                share.expires_at > current_time):
                accessible_shares.append(share)
        
        shared_blocks = {}
        
        for share in accessible_shares:
            # Check if recipient has required access level
            if access_level.value != AccessLevel.READ_ONLY.value and share.access_level != access_level:
                continue
            
            # Get memory blocks from sharing agent
            try:
                memory_blocks = self.client.get_agent_memory(share.sharing_agent_id)
                relevant_blocks = [
                    {
                        "block_id": block.id,
                        "title": block.title,
                        "content": block.content,
                        "block_type": block.block_type.value,
                        "shared_by": share.sharing_agent_id,
                        "share_id": share.share_id
                    }
                    for block in memory_blocks
                    if block.id in share.memory_block_ids
                ]
                
                shared_blocks[share.sharing_agent_id] = relevant_blocks
                
                # Log access
                access_log_entry = {
                    "accessed_by": recipient_agent_id,
                    "accessed_at": datetime.now().isoformat(),
                    "blocks_accessed": len(relevant_blocks)
                }
                share.access_log.append(access_log_entry)
                
            except Exception as e:
                logger.error(f"Failed to retrieve shared memory from {share.sharing_agent_id}: {e}")
        
        return shared_blocks
    
    def revoke_memory_share(self, share_id: str, initiator_agent_id: str) -> bool:
        """Revoke a memory share"""
        
        if share_id not in self.memory_shares:
            logger.error(f"Memory share not found: {share_id}")
            return False
        
        share = self.memory_shares[share_id]
        
        # Check if initiator has permission
        if share.sharing_agent_id != initiator_agent_id:
            logger.error(f"Insufficient permissions to revoke share: {initiator_agent_id}")
            return False
        
        # Remove share
        del self.memory_shares[share_id]
        
        # Notify recipient
        self.send_direct_message(
            sender_agent_id="communication_hub",
            receiver_agent_id=share.recipient_agent_id,
            subject="Memory Share Revoked",
            content=f"Agent {initiator_agent_id} has revoked access to shared memory blocks. "
                   f"Share ID: {share_id}",
            priority=MessagePriority.NORMAL,
            message_type=MessageType.DIRECT
        )
        
        logger.info(f"Memory share revoked: {share_id}")
        return True
    
    # === COORDINATION REQUESTS ===
    
    def initiate_coordination_request(
        self,
        requesting_agent_id: str,
        coordination_type: CoordinationType,
        description: str,
        required_capabilities: List[str],
        participants: List[str],
        priority: MessagePriority = MessagePriority.NORMAL,
        deadline: Optional[datetime] = None
    ) -> Optional[str]:
        """Initiate coordination request between agents"""
        
        if requesting_agent_id not in self.agent_registry:
            logger.error(f"Requesting agent not registered: {requesting_agent_id}")
            return None
        
        request_id = str(uuid.uuid4())
        
        coordination_request = CoordinationRequest(
            request_id=request_id,
            requesting_agent_id=requesting_agent_id,
            coordination_type=coordination_type,
            description=description,
            required_capabilities=required_capabilities,
            participants=participants,
            priority=priority,
            deadline=deadline,
            status="pending",
            created_at=datetime.now(),
            responses=[]
        )
        
        self.coordination_requests[request_id] = coordination_request
        
        # Send coordination request to participants
        for participant_id in participants:
            self.send_direct_message(
                sender_agent_id=requesting_agent_id,
                receiver_agent_id=participant_id,
                subject=f"Coordination Request: {coordination_type.value}",
                content=f"Request: {description}\n\nRequired capabilities: {', '.join(required_capabilities)}\n\n"
                       f"Priority: {priority.value}\n"
                       f"{f'Deadline: {deadline}' if deadline else ''}",
                priority=priority,
                message_type=MessageType.COORDINATION_REQUEST,
                metadata={
                    "request_id": request_id,
                    "coordination_type": coordination_type.value
                }
            )
        
        logger.info(f"Coordination request initiated: {request_id} by {requesting_agent_id}")
        return request_id
    
    def respond_to_coordination_request(
        self,
        agent_id: str,
        request_id: str,
        response: str,  # "accept", "decline", "propose_changes"
        additional_info: str = ""
    ) -> bool:
        """Respond to a coordination request"""
        
        if request_id not in self.coordination_requests:
            logger.error(f"Coordination request not found: {request_id}")
            return False
        
        request = self.coordination_requests[request_id]
        
        # Add response
        response_entry = {
            "agent_id": agent_id,
            "response": response,
            "additional_info": additional_info,
            "timestamp": datetime.now().isoformat()
        }
        request.responses.append(response_entry)
        
        # Update status based on responses
        responses_by_agent = {r["agent_id"]: r["response"] for r in request.responses}
        
        if all(resp in ["accept", "propose_changes"] for resp in responses_by_agent.values()):
            request.status = "accepted"
        elif any(resp == "decline" for resp in responses_by_agent.values()):
            request.status = "declined"
        
        # Notify requesting agent
        self.send_direct_message(
            sender_agent_id="communication_hub",
            receiver_agent_id=request.requesting_agent_id,
            subject=f"Coordination Response: {response}",
            content=f"Agent {agent_id} responded to your coordination request:\n\n"
                   f"Response: {response}\n"
                   f"{f'Additional info: {additional_info}' if additional_info else ''}\n\n"
                   f"Request Status: {request.status}",
            priority=MessagePriority.HIGH,
            message_type=MessageType.COORDINATION_REQUEST,
            metadata={
                "request_id": request_id,
                "responding_agent": agent_id
            }
        )
        
        logger.info(f"Coordination response: {agent_id} -> {request_id}: {response}")
        return True
    
    # === RISK ALERTS ===
    
    def send_risk_alert(
        self,
        source_agent_id: str,
        risk_level: str,
        description: str,
        affected_agents: List[str] = None,
        risk_data: Dict[str, Any] = None,
        mitigation_actions: List[str] = None
    ) -> Optional[str]:
        """Send risk alert to relevant agents"""
        
        alert_id = str(uuid.uuid4())
        
        risk_alert = RiskAlert(
            alert_id=alert_id,
            source_agent_id=source_agent_id,
            risk_level=risk_level,
            description=description,
            affected_agents=affected_agents or [],
            risk_data=risk_data or {},
            mitigation_actions=mitigation_actions or [],
            timestamp=datetime.now(),
            acknowledged_by=[]
        )
        
        # Determine target agents
        if affected_agents:
            target_agents = affected_agents
        else:
            # Send to risk managers and relevant agents
            risk_managers = self.find_agent_by_capability("risk_management")
            target_agents = [agent.agent_id for agent in risk_managers]
        
        # Send alert to each target agent
        alert_count = 0
        for target_agent_id in target_agents:
            if target_agent_id != source_agent_id:  # Don't alert the source
                success = self.send_direct_message(
                    sender_agent_id=source_agent_id,
                    receiver_agent_id=target_agent_id,
                    subject=f"RISK ALERT: {risk_level.upper()}",
                    content=f"Risk Alert from {source_agent_id}:\n\n{description}\n\n"
                           f"Risk Level: {risk_level}\n"
                           f"Alert ID: {alert_id}\n"
                           f"Time: {datetime.now().isoformat()}",
                    priority=MessagePriority.CRITICAL if risk_level == "critical" else MessagePriority.HIGH,
                    message_type=MessageType.RISK_ALERT,
                    metadata={
                        "alert_id": alert_id,
                        "risk_level": risk_level,
                        "source_agent": source_agent_id,
                        "risk_data": risk_data,
                        "mitigation_actions": mitigation_actions
                    }
                )
                if success:
                    alert_count += 1
        
        logger.info(f"Risk alert sent: {alert_id} from {source_agent_id} to {alert_count} agents")
        return alert_id
    
    def acknowledge_risk_alert(self, agent_id: str, alert_id: str) -> bool:
        """Acknowledge a risk alert"""
        
        # In a full implementation, you would store and track alerts
        # For now, just send acknowledgment message
        
        acknowledgment = self.send_direct_message(
            sender_agent_id=agent_id,
            receiver_agent_id="communication_hub",
            subject=f"Risk Alert Acknowledgment",
            content=f"Acknowledged risk alert: {alert_id}",
            priority=MessagePriority.NORMAL,
            message_type=MessageType.RISK_ALERT,
            metadata={
                "alert_id": alert_id,
                "acknowledged_by": agent_id,
                "acknowledged_at": datetime.now().isoformat()
            }
        )
        
        return acknowledgment is not None
    
    # === PERFORMANCE UPDATES ===
    
    def broadcast_performance_update(
        self,
        agent_id: str,
        performance_metrics: Dict[str, Any],
        target_audience: List[AgentRole] = None
    ) -> List[str]:
        """Broadcast performance update to relevant agents"""
        
        # Create performance update message
        update_content = f"Performance Update from {agent_id}:\n\n"
        for metric, value in performance_metrics.items():
            update_content += f"{metric}: {value}\n"
        
        return self.broadcast_message(
            sender_agent_id=agent_id,
            subject="Performance Update",
            content=update_content,
            target_roles=target_audience or [AgentRole.COORDINATOR, AgentRole.ANALYST],
            priority=MessagePriority.NORMAL,
            message_type=MessageType.PERFORMANCE_UPDATE,
            exclude_sender=True
        )
    
    # === ANALYTICS AND MONITORING ===
    
    def get_communication_analytics(
        self,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Get communication analytics and statistics"""
        
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        # Filter messages by time range
        recent_messages = [
            msg for msg in self.message_history
            if msg.timestamp > cutoff_time
        ]
        
        # Calculate statistics
        total_messages = len(recent_messages)
        messages_by_type = {}
        messages_by_priority = {}
        active_agent_pairs = set()
        
        for msg in recent_messages:
            # Count by type
            msg_type = msg.message_type.value
            messages_by_type[msg_type] = messages_by_type.get(msg_type, 0) + 1
            
            # Count by priority
            priority = msg.priority.value
            messages_by_priority[priority] = messages_by_priority.get(priority, 0) + 1
            
            # Track active agent pairs
            agent_pair = tuple(sorted([msg.sender_agent_id, msg.receiver_agent_id]))
            active_agent_pairs.add(agent_pair)
        
        # Calculate average response time (simplified)
        response_times = []
        for i, msg in enumerate(recent_messages[:-1]):
            next_msg = recent_messages[i + 1]
            if (msg.receiver_agent_id == next_msg.sender_agent_id and
                msg.sender_agent_id == next_msg.receiver_agent_id):
                time_diff = (next_msg.timestamp - msg.timestamp).total_seconds()
                if time_diff > 0:  # Only positive time differences
                    response_times.append(time_diff)
        
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # Agent activity
        agent_activity = defaultdict(int)
        for msg in recent_messages:
            agent_activity[msg.sender_agent_id] += 1
            if msg.receiver_agent_id:
                agent_activity[msg.receiver_agent_id] += 1
        
        return {
            "time_range_hours": time_range_hours,
            "total_messages": total_messages,
            "active_agent_pairs": len(active_agent_pairs),
            "messages_by_type": messages_by_type,
            "messages_by_priority": messages_by_priority,
            "average_response_time_seconds": avg_response_time,
            "most_active_agents": dict(sorted(agent_activity.items(), 
                                            key=lambda x: x[1], reverse=True)[:5]),
            "total_registered_agents": len(self.agent_registry),
            "active_collaborations": len(self.active_collaborations),
            "memory_shares": len(self.memory_shares),
            "coordination_requests": len(self.coordination_requests)
        }
    
    def get_agent_communication_profile(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed communication profile for an agent"""
        
        if agent_id not in self.agent_registry:
            return {"error": "Agent not registered"}
        
        registration = self.agent_registry[agent_id]
        
        # Get agent messages
        sent_messages = [
            msg for msg in self.message_history
            if msg.sender_agent_id == agent_id
        ]
        
        received_messages = [
            msg for msg in self.message_history
            if msg.receiver_agent_id == agent_id
        ]
        
        # Calculate statistics
        communication_stats = {
            "agent_info": {
                "id": agent_id,
                "name": registration.name,
                "role": registration.role.value,
                "status": registration.status,
                "availability": registration.availability,
                "performance_score": registration.performance_score
            },
            "communication_activity": {
                "messages_sent": len(sent_messages),
                "messages_received": len(received_messages),
                "total_messages": len(sent_messages) + len(received_messages),
                "active_collaborations": len(registration.active_collaborations)
            },
            "message_types": {},
            "response_patterns": {},
            "recent_messages": []
        }
        
        # Analyze message types
        for msg in sent_messages + received_messages:
            msg_type = msg.message_type.value
            communication_stats["message_types"][msg_type] = \
                communication_stats["message_types"].get(msg_type, 0) + 1
        
        # Get recent messages (last 10)
        recent_messages = sorted(
            sent_messages + received_messages,
            key=lambda x: x.timestamp,
            reverse=True
        )[:10]
        
        communication_stats["recent_messages"] = [
            {
                "timestamp": msg.timestamp.isoformat(),
                "direction": "sent" if msg.sender_agent_id == agent_id else "received",
                "subject": msg.subject[:50] + "..." if len(msg.subject) > 50 else msg.subject,
                "type": msg.message_type.value,
                "priority": msg.priority.value
            }
            for msg in recent_messages
        ]
        
        return communication_stats
    
    # === UTILITY METHODS ===
    
    def cleanup_expired_entries(self):
        """Clean up expired memory shares and coordination requests"""
        
        current_time = datetime.now()
        
        # Clean up expired memory shares
        expired_shares = [
            share_id for share_id, share in self.memory_shares.items()
            if share.expires_at <= current_time
        ]
        
        for share_id in expired_shares:
            del self.memory_shares[share_id]
            logger.info(f"Cleaned up expired memory share: {share_id}")
        
        # Clean up expired coordination requests
        expired_requests = [
            request_id for request_id, request in self.coordination_requests.items()
            if request.deadline and request.deadline <= current_time and request.status == "pending"
        ]
        
        for request_id in expired_requests:
            self.coordination_requests[request_id].status = "expired"
            logger.info(f"Marked coordination request as expired: {request_id}")
        
        return {
            "expired_shares_cleaned": len(expired_shares),
            "expired_requests_cleaned": len(expired_requests)
        }


# === CONVENIENT FACTORY FUNCTIONS ===

def create_communication_hub(client: LettaAPIClient) -> AgentCommunicationHub:
    """Create an agent communication hub instance"""
    return AgentCommunicationHub(client)


def setup_default_agents(hub: AgentCommunicationHub, client: LettaAPIClient):
    """Set up default trading agents in the communication hub"""
    
    # Create default capabilities
    strategist_capabilities = [
        AgentCapability("strategy_development", "Develop and optimize trading strategies", 5, ["strategy", "optimization"]),
        AgentCapability("pattern_recognition", "Identify trading patterns and setups", 4, ["patterns", "analysis"]),
        AgentCapability("risk_assessment", "Assess trading risks and manage exposure", 3, ["risk", "assessment"])
    ]
    
    analyst_capabilities = [
        AgentCapability("market_analysis", "Analyze market conditions and trends", 5, ["market", "analysis"]),
        AgentCapability("data_processing", "Process and analyze trading data", 4, ["data", "processing"]),
        AgentCapability("technical_analysis", "Perform technical analysis", 4, ["technical", "analysis"])
    ]
    
    risk_manager_capabilities = [
        AgentCapability("risk_management", "Manage portfolio risk and exposure", 5, ["risk", "management"]),
        AgentCapability("portfolio_monitoring", "Monitor portfolio performance and risk", 4, ["portfolio", "monitoring"]),
        AgentCapability("compliance", "Ensure regulatory compliance", 3, ["compliance", "regulation"])
    ]
    
    # Register agents (assuming they exist in Letta)
    agents_to_register = [
        ("trading_strategist", "Trading Strategist", AgentRole.STRATEGIST, strategist_capabilities),
        ("market_analyst", "Market Analyst", AgentRole.ANALYST, analyst_capabilities),
        ("risk_manager", "Risk Manager", AgentRole.RISK_MANAGER, risk_manager_capabilities),
        ("coordinator", "Agent Coordinator", AgentRole.COORDINATOR, [
            AgentCapability("coordination", "Coordinate multi-agent activities", 5, ["coordination", "orchestration"]),
            AgentCapability("communication", "Facilitate agent communication", 4, ["communication", "routing"])
        ])
    ]
    
    for agent_id, name, role, capabilities in agents_to_register:
        try:
            # Check if agent exists in Letta
            letta_agent = client.get_agent(agent_id)
            if letta_agent:
                hub.register_agent(agent_id, name, role, capabilities)
                logger.info(f"Registered agent: {name} ({agent_id})")
            else:
                logger.warning(f"Letta agent not found: {agent_id}")
        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")


if __name__ == "__main__":
    # Example usage
    import sys
    sys.path.append('/workspace/code/letta_api')
    
    from letta_client import LettaAPIClient
    
    # Configuration
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8283"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "your-secret-api-key"
    
    print("Agent Communication Hub Demo")
    print("=" * 50)
    
    client = LettaAPIClient(base_url, api_key)
    hub = AgentCommunicationHub(client)
    
    try:
        # Set up default agents
        print("1. Setting up default agents:")
        setup_default_agents(hub, client)
        
        registered_agents = hub.get_registered_agents()
        print(f"   Registered {len(registered_agents)} agents")
        
        # Test direct messaging
        print("\n2. Testing Direct Messaging:")
        if len(registered_agents) >= 2:
            agent1 = registered_agents[0]
            agent2 = registered_agents[1]
            
            message_id = hub.send_direct_message(
                sender_agent_id=agent1.agent_id,
                receiver_agent_id=agent2.agent_id,
                subject="Test Message",
                content="This is a test message between agents",
                priority=MessagePriority.NORMAL
            )
            print(f"   Message sent: {message_id}")
        
        # Test coordination request
        print("\n3. Testing Coordination Request:")
        if len(registered_agents) >= 3:
            coordinator = next((a for a in registered_agents if a.role == AgentRole.COORDINATOR), None)
            if coordinator:
                request_id = hub.initiate_coordination_request(
                    requesting_agent_id=coordinator.agent_id,
                    coordination_type=CoordinationType.TRADE_EXECUTION,
                    description="Coordinate execution of high-confidence trade setup",
                    required_capabilities=["strategy_development", "risk_management"],
                    participants=[a.agent_id for a in registered_agents if a.agent_id != coordinator.agent_id]
                )
                print(f"   Coordination request: {request_id}")
        
        # Test risk alert
        print("\n4. Testing Risk Alert:")
        risk_manager = next((a for a in registered_agents if a.role == AgentRole.RISK_MANAGER), None)
        if risk_manager:
            alert_id = hub.send_risk_alert(
                source_agent_id=risk_manager.agent_id,
                risk_level="medium",
                description="Elevated volatility detected in tech sector positions",
                risk_data={"sector": "technology", "volatility": 0.75},
                mitigation_actions=["Reduce position sizes", "Monitor closely"]
            )
            print(f"   Risk alert sent: {alert_id}")
        
        # Get communication analytics
        print("\n5. Communication Analytics:")
        analytics = hub.get_communication_analytics(time_range_hours=24)
        print(f"   Total messages: {analytics['total_messages']}")
        print(f"   Active agent pairs: {analytics['active_agent_pairs']}")
        print(f"   Average response time: {analytics['average_response_time_seconds']:.2f}s")
        
        print("\nDemo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
    finally:
        client.close()