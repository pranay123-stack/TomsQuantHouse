"""
Human-in-the-Loop Approval Workflow System
Manages approval processes for critical trading decisions
"""
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel
from utils.memory_manager import memory_manager
from config.settings import settings
import logging
import asyncio


class ApprovalType(Enum):
    """Types of approvals required"""
    TRADE_EXECUTION = "trade_execution"
    RISK_VIOLATION = "risk_violation"
    POSITION_LIMIT = "position_limit"
    STRATEGY_CHANGE = "strategy_change"
    MODEL_UPDATE = "model_update"
    EMERGENCY_STOP = "emergency_stop"


class ApprovalStatus(Enum):
    """Approval status types"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PriorityLevel(Enum):
    """Priority levels for approvals"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalRequest(BaseModel):
    """Model for approval requests"""
    request_id: str
    approval_type: ApprovalType
    title: str
    description: str
    requester: str
    priority: PriorityLevel
    created_at: datetime
    expires_at: datetime
    required_approvers: List[str]
    current_approvers: List[str] = []
    status: ApprovalStatus = ApprovalStatus.PENDING
    data: Dict[str, Any] = {}
    decision_notes: str = ""
    decided_at: Optional[datetime] = None


class ApprovalWorkflow:
    """Manages approval workflows and processes"""
    
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.logger = logging.getLogger(__name__)
        self.active_workflows: Dict[str, ApprovalRequest] = {}
        self.approval_handlers: Dict[ApprovalType, Callable] = {}
        
        # Default approval thresholds
        self.thresholds = {
            "trade_amount": settings.approval_required_amount,
            "risk_threshold": settings.high_risk_threshold,
            "position_limit": settings.max_position_size * 0.8,  # 80% of max
        }
    
    async def submit_approval_request(self, 
                                    approval_type: ApprovalType,
                                    title: str,
                                    description: str,
                                    requester: str,
                                    priority: PriorityLevel = PriorityLevel.MEDIUM,
                                    data: Dict[str, Any] = None,
                                    expires_in_hours: int = 24) -> str:
        """Submit a new approval request"""
        try:
            request_id = f"approval_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{approval_type.value}"
            
            # Determine required approvers based on type and priority
            required_approvers = self._determine_required_approvers(approval_type, priority, data)
            
            # Set expiration time
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            
            # Create approval request
            approval_request = ApprovalRequest(
                request_id=request_id,
                approval_type=approval_type,
                title=title,
                description=description,
                requester=requester,
                priority=priority,
                created_at=datetime.now(),
                expires_at=expires_at,
                required_approvers=required_approvers,
                data=data or {}
            )
            
            # Store in memory
            await memory_manager.add_approval_request(self.crew_id, approval_request.dict())
            
            # Add to active workflows
            self.active_workflows[request_id] = approval_request
            
            # Send notifications (implement as needed)
            await self._notify_approvers(required_approvers, approval_request)
            
            self.logger.info(f"Approval request {request_id} submitted by {requester}")
            
            return request_id
            
        except Exception as e:
            self.logger.error(f"Error submitting approval request: {e}")
            raise
    
    async def process_approval(self, 
                             request_id: str,
                             approver: str,
                             decision: ApprovalStatus,
                             notes: str = "") -> bool:
        """Process an approval decision"""
        try:
            if request_id not in self.active_workflows:
                # Try to get from memory
                approval_queue = await memory_manager.get_approval_queue(self.crew_id)
                if request_id in approval_queue:
                    # Restore to active workflows
                    request_data = approval_queue[request_id]
                    self.active_workflows[request_id] = ApprovalRequest(**request_data)
                else:
                    return False
            
            approval_request = self.active_workflows[request_id]
            
            # Validate approver
            if approver not in approval_request.required_approvers:
                self.logger.warning(f"Unauthorized approval attempt by {approver} for {request_id}")
                return False
            
            # Check if already processed
            if approval_request.status != ApprovalStatus.PENDING:
                self.logger.warning(f"Approval request {request_id} already processed")
                return False
            
            # Check expiration
            if datetime.now() > approval_request.expires_at:
                approval_request.status = ApprovalStatus.EXPIRED
                await self._update_approval_in_memory(request_id, approval_request)
                return False
            
            # Record decision
            if approver not in approval_request.current_approvers:
                approval_request.current_approvers.append(approver)
            
            approval_request.status = decision
            approval_request.decision_notes = notes
            approval_request.decided_at = datetime.now()
            
            # Update in memory
            await self._update_approval_in_memory(request_id, approval_request)
            
            # Process approval based on type
            await self._process_approval_by_type(approval_request)
            
            # Send notifications
            await self._notify_all_parties(approval_request)
            
            # Remove from active workflows if completed
            if decision in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
                del self.active_workflows[request_id]
            
            self.logger.info(f"Approval {request_id} {decision.value} by {approver}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing approval {request_id}: {e}")
            return False
    
    async def get_approval_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of approval request"""
        try:
            if request_id in self.active_workflows:
                return self.active_workflows[request_id].dict()
            
            # Try to get from memory
            approval_queue = await memory_manager.get_approval_queue(self.crew_id)
            if request_id in approval_queue:
                return approval_queue[request_id]
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting approval status {request_id}: {e}")
            return None
    
    async def list_pending_approvals(self, approver: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all pending approvals"""
        try:
            approval_queue = await memory_manager.get_approval_queue(self.crew_id)
            
            pending_approvals = []
            for request_id, request_data in approval_queue.items():
                approval_request = ApprovalRequest(**request_data)
                
                # Filter by approver if specified
                if approver and approver not in approval_request.required_approvers:
                    continue
                
                # Check if expired
                if datetime.now() > approval_request.expires_at:
                    approval_request.status = ApprovalStatus.EXPIRED
                    await self._update_approval_in_memory(request_id, approval_request)
                    continue
                
                pending_approvals.append(approval_request.dict())
            
            return pending_approvals
            
        except Exception as e:
            self.logger.error(f"Error listing pending approvals: {e}")
            return []
    
    async def cancel_approval(self, request_id: str, reason: str = "") -> bool:
        """Cancel an approval request"""
        try:
            if request_id in self.active_workflows:
                approval_request = self.active_workflows[request_id]
                approval_request.status = ApprovalStatus.EXPIRED
                approval_request.decision_notes = f"Cancelled: {reason}"
                approval_request.decided_at = datetime.now()
                
                await self._update_approval_in_memory(request_id, approval_request)
                del self.active_workflows[request_id]
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error cancelling approval {request_id}: {e}")
            return False
    
    async def auto_approve_if_safe(self, approval_request: ApprovalRequest) -> bool:
        """Auto-approve if conditions are safe"""
        try:
            if approval_request.priority == PriorityLevel.CRITICAL:
                return False  # Never auto-approve critical items
            
            # Auto-approve based on type and risk assessment
            if approval_request.approval_type == ApprovalType.TRADE_EXECUTION:
                return await self._auto_approve_trade(approval_request)
            elif approval_request.approval_type == ApprovalType.RISK_VIOLATION:
                return await self._auto_approve_risk_violation(approval_request)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in auto-approval check: {e}")
            return False
    
    def _determine_required_approvers(self, 
                                    approval_type: ApprovalType,
                                    priority: PriorityLevel,
                                    data: Dict[str, Any] = None) -> List[str]:
        """Determine required approvers based on type and priority"""
        base_approvers = ["risk_manager", "portfolio_manager"]
        
        # Add approvers based on approval type
        if approval_type == ApprovalType.TRADE_EXECUTION:
            if priority == PriorityLevel.CRITICAL:
                return ["chief_risk_officer", "portfolio_manager", "trading_head"]
            else:
                return ["risk_manager", "portfolio_manager"]
        
        elif approval_type == ApprovalType.RISK_VIOLATION:
            return ["chief_risk_officer", "portfolio_manager"]
        
        elif approval_type == ApprovalType.STRATEGY_CHANGE:
            return ["portfolio_manager", "trading_head", "chief_investment_officer"]
        
        elif approval_type == ApprovalType.EMERGENCY_STOP:
            return ["chief_risk_officer", "trading_head", "ceo"]
        
        elif approval_type == ApprovalType.MODEL_UPDATE:
            return ["quantitative_analyst", "portfolio_manager"]
        
        return base_approvers
    
    async def _notify_approvers(self, approvers: List[str], approval_request: ApprovalRequest):
        """Notify approvers of new request"""
        # In a real implementation, this would send emails, Slack messages, etc.
        self.logger.info(f"Notifying approvers {approvers} of request {approval_request.request_id}")
        
        # Store notification in memory for retrieval
        notification_data = {
            "type": "approval_request",
            "request_id": approval_request.request_id,
            "title": approval_request.title,
            "priority": approval_request.priority.value,
            "approvers": approvers,
            "created_at": approval_request.created_at.isoformat()
        }
        
        await memory_manager.store_crew_memory(
            self.crew_id,
            f"notification_{approval_request.request_id}",
            notification_data,
            ttl=86400  # 24 hours
        )
    
    async def _notify_all_parties(self, approval_request: ApprovalRequest):
        """Notify all relevant parties of decision"""
        notification_data = {
            "type": "approval_decision",
            "request_id": approval_request.request_id,
            "decision": approval_request.status.value,
            "notes": approval_request.decision_notes,
            "decided_at": approval_request.decided_at.isoformat() if approval_request.decided_at else None,
            "requester": approval_request.requester
        }
        
        await memory_manager.store_crew_memory(
            self.crew_id,
            f"decision_notification_{approval_request.request_id}",
            notification_data,
            ttl=86400
        )
    
    async def _update_approval_in_memory(self, request_id: str, approval_request: ApprovalRequest):
        """Update approval request in memory"""
        # Remove from queue (for approved/rejected)
        if approval_request.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            await memory_manager.process_approval_request(
                self.crew_id,
                request_id,
                approval_request.status.value,
                approval_request.decision_notes
            )
        else:
            # Update existing request
            await memory_manager.add_approval_request(self.crew_id, approval_request.dict())
    
    async def _process_approval_by_type(self, approval_request: ApprovalRequest):
        """Process approval based on type"""
        try:
            if approval_request.status == ApprovalStatus.APPROVED:
                if approval_request.approval_type == ApprovalType.TRADE_EXECUTION:
                    await self._execute_approved_trade(approval_request)
                elif approval_request.approval_type == ApprovalType.EMERGENCY_STOP:
                    await self._execute_emergency_stop(approval_request)
                elif approval_request.approval_type == ApprovalType.STRATEGY_CHANGE:
                    await self._update_strategy(approval_request)
            
            elif approval_request.status == ApprovalStatus.REJECTED:
                await self._handle_rejected_approval(approval_request)
                
        except Exception as e:
            self.logger.error(f"Error processing approval by type: {e}")
    
    async def _auto_approve_trade(self, approval_request: ApprovalRequest) -> bool:
        """Auto-approve low-risk trades"""
        try:
            data = approval_request.data
            
            # Check if trade amount is within auto-approve threshold
            trade_amount = data.get("trade_value", 0)
            if trade_amount > self.thresholds["trade_amount"]:
                return False
            
            # Check if within position limits
            current_position = data.get("current_position", 0)
            requested_amount = data.get("requested_amount", 0)
            
            if abs(current_position + requested_amount) > self.thresholds["position_limit"]:
                return False
            
            # Auto-approve if all checks pass
            await self.process_approval(
                approval_request.request_id,
                "auto_approval_system",
                ApprovalStatus.APPROVED,
                "Auto-approved: within safe thresholds"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in auto-approve trade: {e}")
            return False
    
    async def _auto_approve_risk_violation(self, approval_request: ApprovalRequest) -> bool:
        """Auto-approve minor risk violations"""
        try:
            # Only auto-approve if violation is minor
            violation_severity = approval_request.data.get("severity", "high")
            
            if violation_severity == "minor":
                await self.process_approval(
                    approval_request.request_id,
                    "auto_approval_system",
                    ApprovalStatus.APPROVED,
                    "Auto-approved: minor violation"
                )
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in auto-approve risk violation: {e}")
            return False
    
    async def _execute_approved_trade(self, approval_request: ApprovalRequest):
        """Execute trade after approval"""
        self.logger.info(f"Executing approved trade: {approval_request.request_id}")
        # Implementation would integrate with execution system
    
    async def _execute_emergency_stop(self, approval_request: ApprovalRequest):
        """Execute emergency stop after approval"""
        self.logger.warning(f"Executing emergency stop: {approval_request.request_id}")
        # Implementation would integrate with trading system
    
    async def _update_strategy(self, approval_request: ApprovalRequest):
        """Update trading strategy after approval"""
        self.logger.info(f"Updating strategy: {approval_request.request_id}")
        # Implementation would integrate with strategy system
    
    async def _handle_rejected_approval(self, approval_request: ApprovalRequest):
        """Handle rejected approval"""
        self.logger.info(f"Handling rejected approval: {approval_request.request_id}")
        # Implementation would notify relevant systems


class TradeApprovalWorkflow(ApprovalWorkflow):
    """Specialized workflow for trade approvals"""
    
    def __init__(self, crew_id: str):
        super().__init__(crew_id)
        self.trade_validation_rules = {
            "max_single_trade": 50000,
            "max_daily_trades": 100,
            "max_sector_exposure": 0.30,
            "max_correlation_exposure": 0.70
        }
    
    async def submit_trade_approval(self, trade_request: Dict[str, Any], requester: str) -> str:
        """Submit trade for approval"""
        try:
            # Analyze trade risk
            risk_score = await self._analyze_trade_risk(trade_request)
            
            # Determine priority based on risk
            if risk_score > 0.8:
                priority = PriorityLevel.CRITICAL
            elif risk_score > 0.6:
                priority = PriorityLevel.HIGH
            elif risk_score > 0.3:
                priority = PriorityLevel.MEDIUM
            else:
                priority = PriorityLevel.LOW
            
            # Determine if auto-approval is possible
            if priority == PriorityLevel.LOW and await self._check_auto_approval_criteria(trade_request):
                return await self.submit_auto_approved_trade(trade_request, requester)
            
            # Submit for manual approval
            return await self.submit_approval_request(
                approval_type=ApprovalType.TRADE_EXECUTION,
                title=f"Trade Approval: {trade_request.get('symbol', 'Unknown')}",
                description=f"Trade request for {trade_request.get('quantity', 0)} shares of {trade_request.get('symbol', 'Unknown')}",
                requester=requester,
                priority=priority,
                data={"trade_request": trade_request, "risk_score": risk_score}
            )
            
        except Exception as e:
            self.logger.error(f"Error submitting trade approval: {e}")
            raise
    
    async def submit_auto_approved_trade(self, trade_request: Dict[str, Any], requester: str) -> str:
        """Submit trade for auto-approval"""
        request_id = f"auto_trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        approval_request = ApprovalRequest(
            request_id=request_id,
            approval_type=ApprovalType.TRADE_EXECUTION,
            title=f"Auto-Approved Trade: {trade_request.get('symbol', 'Unknown')}",
            description=f"Auto-approved low-risk trade",
            requester=requester,
            priority=PriorityLevel.LOW,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            required_approvers=["auto_approval_system"],
            status=ApprovalStatus.APPROVED
        )
        
        await memory_manager.add_approval_request(self.crew_id, approval_request.dict())
        return request_id
    
    async def _analyze_trade_risk(self, trade_request: Dict[str, Any]) -> float:
        """Analyze risk score for trade"""
        risk_score = 0.0
        
        # Amount risk
        trade_amount = trade_request.get("quantity", 0) * trade_request.get("price", 0)
        if trade_amount > 100000:
            risk_score += 0.3
        elif trade_amount > 50000:
            risk_score += 0.2
        
        # Position risk
        current_position = trade_request.get("current_position", 0)
        if abs(current_position) > 100000:
            risk_score += 0.2
        
        # Sector concentration
        sector_exposure = trade_request.get("sector_exposure", {})
        max_sector = max(sector_exposure.values()) if sector_exposure else 0
        if max_sector > 0.3:
            risk_score += 0.3
        
        return min(risk_score, 1.0)
    
    async def _check_auto_approval_criteria(self, trade_request: Dict[str, Any]) -> bool:
        """Check if trade meets auto-approval criteria"""
        trade_amount = trade_request.get("quantity", 0) * trade_request.get("price", 0)
        
        # Basic criteria
        if trade_amount > self.trade_validation_rules["max_single_trade"]:
            return False
        
        if trade_amount < 1000:  # Minimum for auto-approval
            return False
        
        return True


# Utility functions
async def create_approval_workflow(crew_id: str, workflow_type: str = "general") -> ApprovalWorkflow:
    """Factory function to create approval workflow"""
    if workflow_type == "trade":
        return TradeApprovalWorkflow(crew_id)
    else:
        return ApprovalWorkflow(crew_id)