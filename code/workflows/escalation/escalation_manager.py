"""
Escalation Management System for Critical Trading Decisions
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import uuid

class EscalationLevel(Enum):
    """Escalation levels"""
    SUPERVISOR = 1
    MANAGER = 2
    SENIOR_MANAGEMENT = 3
    EXECUTIVE = 4

class EscalationStatus(Enum):
    """Status of escalation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class EscalationTrigger(Enum):
    """Types of escalation triggers"""
    FINANCIAL_LOSS = "financial_loss_threshold"
    RISK_CRITICAL = "risk_level_critical"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    LOW_CONFIDENCE = "confidence_below_threshold"
    LARGE_POSITION = "large_position_threshold"
    VOLATILITY_SPIKE = "volatility_spike"

@dataclass
class EscalationRequest:
    """Escalation request data"""
    request_id: str
    workflow_id: str
    trigger_type: EscalationTrigger
    level: EscalationLevel
    description: str
    context: Dict[str, Any]
    created_at: datetime
    timeout_minutes: int
    required_approvers: List[str]
    status: EscalationStatus = EscalationStatus.PENDING
    responses: Dict[str, Dict[str, Any]] = None
    resolved_at: Optional[datetime] = None

@dataclass
class ApproverResponse:
    """Response from an approver"""
    approver_id: str
    decision: str  # "approve", "reject", "request_more_info"
    comments: str
    timestamp: datetime
    confidence_level: float

class EscalationManager:
    """Manages escalation workflows for critical decisions"""
    
    def __init__(self, workflows_dir: str = "code/workflows"):
        self.workflows_dir = workflows_dir
        self.active_escalations: Dict[str, EscalationRequest] = {}
        self.escalation_history: List[EscalationRequest] = []
        self.escalation_rules: Dict[str, Any] = {}
        self.notification_system = None  # Would be actual notification service
        self.approver_directory: Dict[str, Dict[str, Any]] = {}
        self.load_escalation_rules()
        self.load_approver_directory()
    
    def load_escalation_rules(self):
        """Load escalation rules from configuration"""
        rules_file = f"{self.workflows_dir}/escalation/rules.json"
        try:
            with open(rules_file, 'r') as f:
                self.escalation_rules = json.load(f)
        except FileNotFoundError:
            self.create_default_rules()
    
    def load_approver_directory(self):
        """Load approver directory"""
        self.approver_directory = {
            "trading_supervisor": {
                "name": "Trading Supervisor",
                "level": EscalationLevel.SUPERVISOR,
                "contact_methods": ["email", "dashboard"],
                "availability": "business_hours",
                "max_escalations_per_day": 50
            },
            "trading_manager": {
                "name": "Trading Manager", 
                "level": EscalationLevel.MANAGER,
                "contact_methods": ["email", "sms", "dashboard"],
                "availability": "business_hours_extended",
                "max_escalations_per_day": 30
            },
            "risk_manager": {
                "name": "Risk Manager",
                "level": EscalationLevel.MANAGER,
                "contact_methods": ["email", "sms", "phone", "dashboard"],
                "availability": "24_7",
                "max_escalations_per_day": 100
            },
            "head_of_trading": {
                "name": "Head of Trading",
                "level": EscalationLevel.SENIOR_MANAGEMENT,
                "contact_methods": ["email", "sms", "phone", "dashboard"],
                "availability": "business_hours_extended",
                "max_escalations_per_day": 20
            },
            "chief_risk_officer": {
                "name": "Chief Risk Officer",
                "level": EscalationLevel.SENIOR_MANAGEMENT,
                "contact_methods": ["phone", "sms", "email", "dashboard"],
                "availability": "24_7",
                "max_escalations_per_day": 50
            },
            "ceo": {
                "name": "Chief Executive Officer",
                "level": EscalationLevel.EXECUTIVE,
                "contact_methods": ["phone", "sms"],
                "availability": "emergency_only",
                "max_escalations_per_day": 5
            },
            "cto": {
                "name": "Chief Technology Officer", 
                "level": EscalationLevel.EXECUTIVE,
                "contact_methods": ["phone", "sms", "email"],
                "availability": "emergency_only",
                "max_escalations_per_day": 10
            },
            "cfo": {
                "name": "Chief Financial Officer",
                "level": EscalationLevel.EXECUTIVE,
                "contact_methods": ["phone", "sms", "email"],
                "availability": "emergency_only", 
                "max_escalations_per_day": 10
            }
        }
    
    def create_default_rules(self):
        """Create default escalation rules"""
        self.escalation_rules = {
            "escalation_levels": [
                {
                    "level": 1,
                    "name": "Supervisor Review",
                    "timeout_minutes": 15,
                    "required_approvers": ["trading_supervisor"]
                },
                {
                    "level": 2,
                    "name": "Manager Escalation", 
                    "timeout_minutes": 10,
                    "required_approvers": ["trading_manager", "risk_manager"]
                },
                {
                    "level": 3,
                    "name": "Senior Management",
                    "timeout_minutes": 5,
                    "required_approvers": ["head_of_trading", "chief_risk_officer"]
                },
                {
                    "level": 4,
                    "name": "Executive Escalation",
                    "timeout_minutes": 3,
                    "required_approvers": ["ceo", "cto", "cfo"]
                }
            ]
        }
    
    async def trigger_escalation(self, workflow_id: str, trigger_type: EscalationTrigger,
                               context: Dict[str, Any]) -> str:
        """Trigger an escalation based on conditions"""
        
        # Determine escalation level based on trigger
        level = self.determine_escalation_level(trigger_type, context)
        if not level:
            return None
        
        # Check if escalation is appropriate
        if not self.should_escalate(trigger_type, context):
            return None
        
        # Create escalation request
        request = self.create_escalation_request(workflow_id, trigger_type, level, context)
        
        # Add to active escalations
        self.active_escalations[request.request_id] = request
        
        # Start escalation process
        asyncio.create_task(self.process_escalation(request))
        
        return request.request_id
    
    def determine_escalation_level(self, trigger_type: EscalationTrigger, 
                                 context: Dict[str, Any]) -> Optional[EscalationLevel]:
        """Determine appropriate escalation level"""
        
        # Financial loss threshold
        if trigger_type == EscalationTrigger.FINANCIAL_LOSS:
            loss_percentage = context.get('loss_percentage', 0)
            if loss_percentage > 0.1:  # >10% loss
                return EscalationLevel.EXECUTIVE
            elif loss_percentage > 0.05:  # >5% loss
                return EscalationLevel.SENIOR_MANAGEMENT
            else:
                return EscalationLevel.MANAGER
        
        # Risk critical
        elif trigger_type == EscalationTrigger.RISK_CRITICAL:
            return EscalationLevel.EXECUTIVE
        
        # Large position
        elif trigger_type == EscalationTrigger.LARGE_POSITION:
            position_size = context.get('position_value', 0)
            if position_size > 10000000:  # >$10M
                return EscalationLevel.EXECUTIVE
            elif position_size > 5000000:  # >$5M
                return EscalationLevel.SENIOR_MANAGEMENT
            else:
                return EscalationLevel.MANAGER
        
        # Volatility spike
        elif trigger_type == EscalationTrigger.VOLATILITY_SPIKE:
            return EscalationLevel.MANAGER
        
        # Low confidence
        elif trigger_type == EscalationTrigger.LOW_CONFIDENCE:
            return EscalationLevel.SUPERVISOR
        
        # Consecutive failures
        elif trigger_type == EscalationTrigger.CONSECUTIVE_FAILURES:
            return EscalationLevel.MANAGER
        
        return EscalationLevel.SUPERVISOR
    
    def should_escalate(self, trigger_type: EscalationTrigger, context: Dict[str, Any]) -> bool:
        """Determine if escalation should be triggered"""
        
        # Check time-based restrictions
        current_time = datetime.utcnow()
        current_hour = current_time.hour
        
        # Some escalations only during business hours
        business_hour_triggers = [EscalationTrigger.LOW_CONFIDENCE, EscalationTrigger.CONSECUTIVE_FAILURES]
        if trigger_type in business_hour_triggers:
            if not (9 <= current_hour <= 17):  # Outside business hours
                # Allow for high-priority triggers
                if trigger_type != EscalationTrigger.LOW_CONFIDENCE:
                    return False
        
        # Check rate limiting
        if self.is_rate_limited(trigger_type, context.get('agent_id', 'unknown')):
            return False
        
        # Check for duplicate escalations
        if self.has_recent_similar_escalation(trigger_type, context.get('workflow_id'), 300):  # 5 minutes
            return False
        
        return True
    
    def is_rate_limited(self, trigger_type: EscalationTrigger, agent_id: str) -> bool:
        """Check if escalation is rate limited"""
        # Simplified rate limiting - in reality would use Redis or similar
        recent_escalations = [
            e for e in self.active_escalations.values()
            if e.trigger_type == trigger_type and e.created_at > datetime.utcnow() - timedelta(minutes=10)
        ]
        
        # Limit based on trigger type
        limits = {
            EscalationTrigger.FINANCIAL_LOSS: 5,
            EscalationTrigger.RISK_CRITICAL: 10,
            EscalationTrigger.CONSECUTIVE_FAILURES: 3,
            EscalationTrigger.LOW_CONFIDENCE: 20,
            EscalationTrigger.LARGE_POSITION: 10,
            EscalationTrigger.VOLATILITY_SPIKE: 15
        }
        
        limit = limits.get(trigger_type, 10)
        return len(recent_escalations) >= limit
    
    def has_recent_similar_escalation(self, trigger_type: EscalationTrigger, 
                                    workflow_id: str, seconds: int) -> bool:
        """Check for recent similar escalations"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=seconds)
        
        for escalation in self.escalation_history:
            if (escalation.trigger_type == trigger_type and 
                escalation.workflow_id == workflow_id and
                escalation.created_at > cutoff_time):
                return True
        
        return False
    
    def create_escalation_request(self, workflow_id: str, trigger_type: EscalationTrigger,
                                level: EscalationLevel, context: Dict[str, Any]) -> EscalationRequest:
        """Create an escalation request"""
        
        request_id = f"esc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Get escalation level configuration
        level_config = None
        for esc_level in self.escalation_rules.get('escalation_levels', []):
            if esc_level['level'] == level.value:
                level_config = esc_level
                break
        
        if not level_config:
            level_config = {'timeout_minutes': 15, 'required_approvers': ['trading_supervisor']}
        
        # Create request
        request = EscalationRequest(
            request_id=request_id,
            workflow_id=workflow_id,
            trigger_type=trigger_type,
            level=level,
            description=self.generate_escalation_description(trigger_type, context),
            context=context,
            created_at=datetime.utcnow(),
            timeout_minutes=level_config['timeout_minutes'],
            required_approvers=level_config['required_approvers'],
            status=EscalationStatus.PENDING
        )
        
        return request
    
    def generate_escalation_description(self, trigger_type: EscalationTrigger, 
                                      context: Dict[str, Any]) -> str:
        """Generate description for escalation"""
        
        descriptions = {
            EscalationTrigger.FINANCIAL_LOSS: f"Financial loss threshold exceeded: {context.get('loss_percentage', 0):.2%}",
            EscalationTrigger.RISK_CRITICAL: f"Critical risk level detected: {context.get('risk_assessment', 'unknown')}",
            EscalationTrigger.CONSECUTIVE_FAILURES: f"Consecutive failures detected: {context.get('failure_count', 0)}",
            EscalationTrigger.LOW_CONFIDENCE: f"Low confidence score: {context.get('confidence', 0):.2f}",
            EscalationTrigger.LARGE_POSITION: f"Large position detected: ${context.get('position_value', 0):,.0f}",
            EscalationTrigger.VOLATILITY_SPIKE: f"Volatility spike detected: {context.get('volatility_increase', 0):.2%}"
        }
        
        return descriptions.get(trigger_type, "Unknown escalation trigger")
    
    async def process_escalation(self, request: EscalationRequest):
        """Process an escalation request"""
        
        try:
            request.status = EscalationStatus.IN_PROGRESS
            
            # Notify approvers
            await self.notify_approvers(request)
            
            # Wait for responses or timeout
            await self.wait_for_responses(request)
            
        except Exception as e:
            print(f"Error processing escalation {request.request_id}: {e}")
            request.status = EscalationStatus.TIMEOUT
        finally:
            # Move to history
            request.resolved_at = datetime.utcnow()
            self.escalation_history.append(request)
            if request.request_id in self.active_escalations:
                del self.active_escalations[request.request_id]
    
    async def notify_approvers(self, request: EscalationRequest):
        """Notify approvers of escalation request"""
        
        # Get notification template
        template = self.get_notification_template(request.level)
        
        # Send notifications
        for approver_id in request.required_approvers:
            approver_info = self.approver_directory.get(approver_id, {})
            contact_methods = approver_info.get('contact_methods', ['email'])
            
            notification = {
                'request_id': request.request_id,
                'approver_id': approver_id,
                'message': template['message'].format(
                    workflow_id=request.workflow_id,
                    trigger_type=request.trigger_type.value,
                    description=request.description
                ),
                'urgency': template['urgency'],
                'deadline': request.created_at + timedelta(minutes=request.timeout_minutes),
                'context': request.context
            }
            
            # In a real implementation, send actual notifications
            await self.send_notification(notification, contact_methods)
    
    def get_notification_template(self, level: EscalationLevel) -> Dict[str, Any]:
        """Get notification template for escalation level"""
        
        templates = {
            EscalationLevel.SUPERVISOR: {
                'subject': 'Trading Decision Review Required',
                'message': 'Workflow {workflow_id} requires supervisor review: {description}',
                'urgency': 'medium'
            },
            EscalationLevel.MANAGER: {
                'subject': 'URGENT: Management Escalation Required',
                'message': 'CRITICAL: {description} - Immediate management approval required',
                'urgency': 'high'
            },
            EscalationLevel.SENIOR_MANAGEMENT: {
                'subject': 'CRITICAL: Senior Management Approval Required',
                'message': 'EMERGENCY: {description} - Senior management approval required within 5 minutes',
                'urgency': 'critical'
            },
            EscalationLevel.EXECUTIVE: {
                'subject': 'EMERGENCY: Executive Approval Required',
                'message': 'EMERGENCY: {description} - Immediate executive intervention required',
                'urgency': 'emergency'
            }
        }
        
        return templates.get(level, templates[EscalationLevel.SUPERVISOR])
    
    async def send_notification(self, notification: Dict[str, Any], 
                              contact_methods: List[str]):
        """Send notification via specified methods"""
        
        # In a real implementation, this would send actual notifications
        # For simulation, we'll just log
        print(f"NOTIFICATION: {notification['urgency']} - {notification['message']}")
        print(f"Methods: {contact_methods}")
        print(f"Deadline: {notification['deadline']}")
    
    async def wait_for_responses(self, request: EscalationRequest):
        """Wait for approver responses or timeout"""
        
        timeout = request.timeout_minutes * 60  # Convert to seconds
        start_time = datetime.utcnow()
        
        # Track responses
        responses = {}
        required_count = len(request.required_approvers)
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            # Check for responses (in reality, would poll or use callbacks)
            await asyncio.sleep(1)  # Check every second
            
            # Simulate approver responses
            if self.should_simulate_response(request):
                response = self.simulate_approver_response(request)
                approver_id = response.approver_id
                
                if approver_id not in responses:
                    responses[approver_id] = response
                    
                    # If critical approval received, may proceed early
                    if response.decision == "approve" and self.is_critical_approval(request):
                        break
            
            # Check if we have enough approvals
            approvals = [r for r in responses.values() if r.decision == "approve"]
            if len(approvals) >= required_count:
                request.status = EscalationStatus.APPROVED
                return
        
        # Check timeout
        if datetime.utcnow() - start_time >= timedelta(seconds=timeout):
            if not responses:
                request.status = EscalationStatus.TIMEOUT
            else:
                # Partial responses - decide based on approval ratio
                approvals = [r for r in responses.values() if r.decision == "approve"]
                if len(approvals) / len(request.required_approvers) >= 0.5:
                    request.status = EscalationStatus.APPROVED
                else:
                    request.status = EscalationStatus.REJECTED
        
        request.responses = {r.approver_id: asdict(r) for r in responses.values()}
    
    def should_simulate_response(self, request: EscalationRequest) -> bool:
        """Determine if we should simulate an approver response"""
        # Simulate responses based on escalation level and trigger type
        import random
        
        response_probability = {
            EscalationLevel.SUPERVISOR: 0.8,
            EscalationLevel.MANAGER: 0.7,
            EscalationLevel.SENIOR_MANAGEMENT: 0.5,
            EscalationLevel.EXECUTIVE: 0.3
        }
        
        prob = response_probability.get(request.level, 0.5)
        return random.random() < prob
    
    def simulate_approver_response(self, request: EscalationRequest) -> ApproverResponse:
        """Simulate approver response"""
        import random
        
        # Select random approver
        approver_id = random.choice(request.required_approvers)
        
        # Simulate decision based on context
        approval_probability = 0.7  # 70% approval rate
        
        if request.trigger_type == EscalationTrigger.RISK_CRITICAL:
            approval_probability = 0.9  # Higher approval for risk issues
        elif request.trigger_type == EscalationTrigger.FINANCIAL_LOSS:
            approval_probability = 0.6  # Lower approval for losses
        
        decision = "approve" if random.random() < approval_probability else "reject"
        
        return ApproverResponse(
            approver_id=approver_id,
            decision=decision,
            comments=f"Auto-generated {decision} response",
            timestamp=datetime.utcnow(),
            confidence_level=random.uniform(0.7, 1.0)
        )
    
    def is_critical_approval(self, request: EscalationRequest) -> bool:
        """Check if approval is critical and allows early proceed"""
        # Some approvals are critical and can allow early action
        critical_approvers = ["risk_manager", "chief_risk_officer"]
        responses = getattr(request, 'responses', {})
        
        for approver_id in critical_approvers:
            if approver_id in request.required_approvers:
                return True
        
        return False
    
    def get_escalation_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of escalation request"""
        
        # Check active escalations
        if request_id in self.active_escalations:
            request = self.active_escalations[request_id]
            return asdict(request)
        
        # Check history
        for request in self.escalation_history:
            if request.request_id == request_id:
                return asdict(request)
        
        return None
    
    def get_escalation_metrics(self) -> Dict[str, Any]:
        """Get escalation metrics"""
        
        total_escalations = len(self.escalation_history)
        if total_escalations == 0:
            return {'error': 'No escalations processed yet'}
        
        # Calculate metrics
        status_counts = defaultdict(int)
        level_counts = defaultdict(int)
        trigger_counts = defaultdict(int)
        
        total_resolution_time = 0
        approved_count = 0
        
        for request in self.escalation_history:
            status_counts[request.status.value] += 1
            level_counts[request.level.value] += 1
            trigger_counts[request.trigger_type.value] += 1
            
            if request.resolved_at:
                resolution_time = (request.resolved_at - request.created_at).total_seconds()
                total_resolution_time += resolution_time
            
            if request.status == EscalationStatus.APPROVED:
                approved_count += 1
        
        avg_resolution_time = total_resolution_time / total_escalations
        approval_rate = approved_count / total_escalations
        
        return {
            'total_escalations': total_escalations,
            'status_distribution': dict(status_counts),
            'level_distribution': dict(level_counts),
            'trigger_distribution': dict(trigger_counts),
            'approval_rate': approval_rate,
            'average_resolution_time_seconds': avg_resolution_time,
            'active_escalations': len(self.active_escalations)
        }