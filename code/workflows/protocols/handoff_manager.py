"""
Agent Handoff Protocols - Context Preservation and Transfer Mechanisms
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class HandoffMethod(Enum):
    """Methods of agent handoff"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    EMERGENCY = "emergency"

class TransferStatus(Enum):
    """Status of handoff transfer"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"

@dataclass
class HandoffContext:
    """Context object for agent handoff"""
    workflow_id: str
    from_agent: str
    to_agent: str
    handoff_method: HandoffMethod
    timestamp: datetime
    data_transferred: Dict[str, Any]
    preservation_required: bool
    rollback_available: bool
    transfer_id: str

@dataclass
class HandoffProtocol:
    """Protocol definition for agent handoff"""
    protocol_id: str
    name: str
    description: str
    handoff_method: HandoffMethod
    required_data: List[str]
    preservation_rules: Dict[str, Any]
    timeout_seconds: int
    retry_count: int = 0
    max_retries: int = 3
    requires_acknowledgment: bool = True

class AgentHandoffManager:
    """Manages agent handoffs with context preservation"""
    
    def __init__(self, workflows_dir: str = "code/workflows"):
        self.workflows_dir = workflows_dir
        self.active_handoffs: Dict[str, HandoffContext] = {}
        self.handoff_protocols: Dict[str, HandoffProtocol] = {}
        self.transfer_history: List[Dict[str, Any]] = []
        self.load_protocols()
    
    def load_protocols(self):
        """Load handoff protocols from configuration"""
        protocols_dir = f"{self.workflows_dir}/protocols"
        
        protocol_files = {
            "sequential_transfer.json": HandoffMethod.SEQUENTIAL,
            "parallel_processing.json": HandoffMethod.PARALLEL,
            "conditional_routing.json": HandoffMethod.CONDITIONAL,
            "emergency_escalation.json": HandoffMethod.EMERGENCY
        }
        
        for filename, method in protocol_files.items():
            try:
                with open(f"{protocols_dir}/{filename}", 'r') as f:
                    protocol_data = json.load(f)
                    self.handoff_protocols[protocol_data['protocol_id']] = HandoffProtocol(
                        protocol_id=protocol_data['protocol_id'],
                        name=protocol_data['name'],
                        description=protocol_data['description'],
                        handoff_method=method,
                        required_data=protocol_data.get('required_data', []),
                        preservation_rules=protocol_data.get('preservation_rules', {}),
                        timeout_seconds=protocol_data.get('timeout_seconds', 300),
                        retry_count=protocol_data.get('retry_count', 0),
                        max_retries=protocol_data.get('max_retries', 3),
                        requires_acknowledgment=protocol_data.get('requires_acknowledgment', True)
                    )
            except FileNotFoundError:
                # Create default protocol if file doesn't exist
                default_protocol = self.create_default_protocol(method)
                self.handoff_protocols[default_protocol.protocol_id] = default_protocol
    
    def create_default_protocol(self, method: HandoffMethod) -> HandoffProtocol:
        """Create default protocol for handoff method"""
        protocol_id = f"default_{method.value}"
        
        if method == HandoffMethod.SEQUENTIAL:
            return HandoffProtocol(
                protocol_id=protocol_id,
                name="Sequential Agent Transfer",
                description="Standard sequential handoff between agents",
                handoff_method=method,
                required_data=["current_state", "relevant_data", "decision_history"],
                preservation_rules={
                    "preserve_history": True,
                    "validate_context": True,
                    "checkpoint_before_transfer": True
                },
                timeout_seconds=300,
                requires_acknowledgment=True
            )
        elif method == HandoffMethod.PARALLEL:
            return HandoffProtocol(
                protocol_id=protocol_id,
                name="Parallel Agent Processing",
                description="Multiple agents processing simultaneously",
                handoff_method=method,
                required_data=["input_data", "processing_parameters"],
                preservation_rules={
                    "merge_results": True,
                    "track_individual_results": True,
                    "timeout_handling": "longest_timeout"
                },
                timeout_seconds=600,
                requires_acknowledgment=False
            )
        elif method == HandoffMethod.CONDITIONAL:
            return HandoffProtocol(
                protocol_id=protocol_id,
                name="Conditional Agent Routing",
                description="Context-based agent selection and routing",
                handoff_method=method,
                required_data=["decision_criteria", "context_evaluation"],
                preservation_rules={
                    "evaluate_conditions": True,
                    "preserve_decision_path": True,
                    "enable_rollback": True
                },
                timeout_seconds=180,
                requires_acknowledgment=True
            )
        else:  # EMERGENCY
            return HandoffProtocol(
                protocol_id=protocol_id,
                name="Emergency Agent Escalation",
                description="Rapid handoff for emergency situations",
                handoff_method=method,
                required_data=["critical_state", "immediate_risks", "escalation_reason"],
                preservation_rules={
                    "bypass_validation": True,
                    "priority_handling": True,
                    "full_context_transfer": True
                },
                timeout_seconds=30,
                requires_acknowledgment=True
            )
    
    async def initiate_handoff(self, workflow_id: str, from_agent: str, to_agent: str,
                             handoff_method: HandoffMethod, data: Dict[str, Any],
                             preservation_required: bool = True) -> str:
        """Initiate agent handoff with context preservation"""
        
        transfer_id = f"handoff_{workflow_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Get or create protocol
        protocol = self.handoff_protocols.get(f"default_{handoff_method.value}")
        if not protocol:
            protocol = self.create_default_protocol(handoff_method)
            self.handoff_protocols[protocol.protocol_id] = protocol
        
        # Create handoff context
        handoff_context = HandoffContext(
            workflow_id=workflow_id,
            from_agent=from_agent,
            to_agent=to_agent,
            handoff_method=handoff_method,
            timestamp=datetime.utcnow(),
            data_transferred=self.prepare_transfer_data(data, protocol),
            preservation_required=preservation_required,
            rollback_available=preservation_required,
            transfer_id=transfer_id
        )
        
        self.active_handoffs[transfer_id] = handoff_context
        
        # Execute handoff based on method
        try:
            if handoff_method == HandoffMethod.SEQUENTIAL:
                result = await self._execute_sequential_handoff(handoff_context, protocol)
            elif handoff_method == HandoffMethod.PARALLEL:
                result = await self._execute_parallel_handoff(handoff_context, protocol)
            elif handoff_method == HandoffMethod.CONDITIONAL:
                result = await self._execute_conditional_handoff(handoff_context, protocol)
            else:  # EMERGENCY
                result = await self._execute_emergency_handoff(handoff_context, protocol)
            
            # Update transfer history
            self.transfer_history.append({
                'transfer_id': transfer_id,
                'workflow_id': workflow_id,
                'from_agent': from_agent,
                'to_agent': to_agent,
                'method': handoff_method.value,
                'status': 'completed',
                'timestamp': datetime.utcnow().isoformat(),
                'duration_seconds': (datetime.utcnow() - handoff_context.timestamp).total_seconds()
            })
            
            return result
            
        except Exception as e:
            # Handle handoff failure
            await self._handle_handoff_failure(transfer_id, str(e))
            raise e
        
        finally:
            # Clean up active handoff
            if transfer_id in self.active_handoffs:
                del self.active_handoffs[transfer_id]
    
    def prepare_transfer_data(self, data: Dict[str, Any], protocol: HandoffProtocol) -> Dict[str, Any]:
        """Prepare data for transfer according to protocol rules"""
        transferred_data = {}
        
        # Transfer required data
        for field in protocol.required_data:
            if field in data:
                transferred_data[field] = data[field]
        
        # Apply preservation rules
        if protocol.preservation_rules.get('preserve_history'):
            transferred_data['transfer_history'] = self.transfer_history[-10:]  # Last 10 transfers
        
        if protocol.preservation_rules.get('validate_context'):
            transferred_data['validation_timestamp'] = datetime.utcnow().isoformat()
        
        if protocol.preservation_rules.get('checkpoint_before_transfer'):
            transferred_data['checkpoint_data'] = self.create_checkpoint(data)
        
        return transferred_data
    
    def create_checkpoint(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create checkpoint for rollback capability"""
        return {
            'checkpoint_timestamp': datetime.utcnow().isoformat(),
            'data_snapshot': data.copy(),
            'checksum': self._calculate_checksum(data)
        }
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for data integrity verification"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    async def _execute_sequential_handoff(self, context: HandoffContext, 
                                        protocol: HandoffProtocol) -> str:
        """Execute sequential handoff"""
        # Validate incoming agent is ready
        await self._validate_agent_ready(context.to_agent)
        
        # Transfer data
        await self._transfer_data(context, protocol)
        
        # Wait for acknowledgment
        if protocol.requires_acknowledgment:
            acknowledgment = await self._wait_for_acknowledgment(context.transfer_id, protocol.timeout_seconds)
            if not acknowledgment:
                raise TimeoutError(f"Acknowledgment timeout for transfer {context.transfer_id}")
        
        return context.transfer_id
    
    async def _execute_parallel_handoff(self, context: HandoffContext,
                                      protocol: HandoffProtocol) -> str:
        """Execute parallel handoff"""
        # Start parallel processing
        tasks = []
        
        # Main handoff
        main_task = asyncio.create_task(self._execute_sequential_handoff(context, protocol))
        tasks.append(main_task)
        
        # Additional parallel tasks (e.g., validation, monitoring)
        validation_task = asyncio.create_task(self._validate_parallel_handoff(context))
        tasks.append(validation_task)
        
        # Wait for completion
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise Exception(f"Parallel task {i} failed: {result}")
        
        return context.transfer_id
    
    async def _execute_conditional_handoff(self, context: HandoffContext,
                                         protocol: HandoffProtocol) -> str:
        """Execute conditional handoff"""
        # Evaluate conditions
        conditions = context.data_transferred.get('decision_criteria', {})
        should_proceed = self._evaluate_handoff_conditions(conditions, context)
        
        if not should_proceed:
            # Rollback or redirect
            await self._execute_rollback(context)
            raise Exception("Handoff conditions not met")
        
        # Proceed with sequential handoff
        return await self._execute_sequential_handoff(context, protocol)
    
    async def _execute_emergency_handoff(self, context: HandoffContext,
                                       protocol: HandoffProtocol) -> str:
        """Execute emergency handoff"""
        # Bypass normal validation for emergency
        await self._transfer_data(context, protocol, bypass_validation=True)
        
        # Force acknowledgment
        acknowledgment = await self._force_acknowledgment(context.transfer_id, 30)
        if not acknowledgment:
            # Emergency fallback
            await self._emergency_fallback(context)
            raise Exception("Emergency handoff failed - fallback initiated")
        
        return context.transfer_id
    
    async def _validate_agent_ready(self, agent: str) -> bool:
        """Validate that target agent is ready to receive handoff"""
        # In a real implementation, this would check agent health/availability
        # For now, simulate validation
        await asyncio.sleep(0.1)  # Simulate network call
        return True
    
    async def _transfer_data(self, context: HandoffContext, protocol: HandoffProtocol,
                           bypass_validation: bool = False) -> bool:
        """Transfer data to target agent"""
        # Simulate data transfer
        if not bypass_validation:
            # Validate data integrity
            checksum = context.data_transferred.get('checksum')
            if checksum and not self._verify_checksum(context.data_transferred, checksum):
                raise Exception("Data integrity check failed")
        
        # Simulate transfer time
        await asyncio.sleep(0.2)
        
        return True
    
    def _verify_checksum(self, data: Dict[str, Any], expected_checksum: str) -> bool:
        """Verify data checksum"""
        calculated_checksum = self._calculate_checksum(data)
        return calculated_checksum == expected_checksum
    
    async def _wait_for_acknowledgment(self, transfer_id: str, timeout: int) -> bool:
        """Wait for acknowledgment from target agent"""
        # Simulate waiting for acknowledgment
        await asyncio.sleep(min(0.1, timeout / 10))  # Simulate shorter wait time
        return True  # Simulate successful acknowledgment
    
    async def _validate_parallel_handoff(self, context: HandoffContext) -> bool:
        """Validate parallel handoff setup"""
        # Check that parallel setup is valid
        await asyncio.sleep(0.1)  # Simulate validation
        return True
    
    def _evaluate_handoff_conditions(self, conditions: Dict[str, Any], 
                                   context: HandoffContext) -> bool:
        """Evaluate conditions for conditional handoff"""
        # Evaluate basic conditions
        for field, condition in conditions.items():
            if field not in context.data_transferred:
                return False
        
        return True
    
    async def _execute_rollback(self, context: HandoffContext) -> bool:
        """Execute rollback of failed handoff"""
        if context.rollback_available:
            checkpoint_data = context.data_transferred.get('checkpoint_data', {})
            if checkpoint_data:
                # Restore from checkpoint
                await self._restore_from_checkpoint(checkpoint_data)
                return True
        return False
    
    async def _restore_from_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        """Restore data from checkpoint"""
        # Simulate restoration
        await asyncio.sleep(0.1)
        return True
    
    async def _force_acknowledgment(self, transfer_id: str, timeout: int) -> bool:
        """Force acknowledgment for emergency handoff"""
        # Shorter timeout for emergency
        return await self._wait_for_acknowledgment(transfer_id, min(timeout, 10))
    
    async def _emergency_fallback(self, context: HandoffContext) -> bool:
        """Execute emergency fallback procedures"""
        # Log emergency
        print(f"EMERGENCY FALLBACK: Transfer {context.transfer_id} failed")
        
        # Attempt manual intervention or different routing
        return True
    
    async def _handle_handoff_failure(self, transfer_id: str, error: str) -> None:
        """Handle handoff failure"""
        # Update transfer history with failure
        self.transfer_history.append({
            'transfer_id': transfer_id,
            'status': 'failed',
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_handoff_status(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get status of ongoing handoff"""
        if transfer_id in self.active_handoffs:
            context = self.active_handoffs[transfer_id]
            return asdict(context)
        
        # Check transfer history
        for transfer in self.transfer_history:
            if transfer['transfer_id'] == transfer_id:
                return transfer
        
        return None
    
    def get_transfer_metrics(self) -> Dict[str, Any]:
        """Get handoff transfer metrics"""
        total_transfers = len(self.transfer_history)
        successful_transfers = len([t for t in self.transfer_history if t['status'] == 'completed'])
        failed_transfers = len([t for t in self.transfer_history if t['status'] == 'failed'])
        
        avg_duration = 0
        if total_transfers > 0:
            durations = [t.get('duration_seconds', 0) for t in self.transfer_history if 'duration_seconds' in t]
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_transfers': total_transfers,
            'successful_transfers': successful_transfers,
            'failed_transfers': failed_transfers,
            'success_rate': successful_transfers / total_transfers if total_transfers > 0 else 0,
            'average_duration_seconds': avg_duration,
            'active_handoffs': len(self.active_handoffs)
        }