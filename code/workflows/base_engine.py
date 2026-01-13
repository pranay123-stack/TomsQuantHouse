"""
Base Workflow Engine for Agent Handoff and Decision Making
Provides core workflow orchestration and context management
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from pathlib import Path

class WorkflowState(Enum):
    """Workflow execution states"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class DecisionType(Enum):
    """Types of decisions requiring routing"""
    AUTOMATED = "automated"
    HUMAN_REQUIRED = "human_required"
    ESCALATED = "escalated"
    CONFLICT_RESOLUTION = "conflict_resolution"

@dataclass
class WorkflowContext:
    """Context object for preserving state across agent handoffs"""
    workflow_id: str
    scenario_type: str
    current_agent: Optional[str]
    previous_agents: List[str]
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    priority: int
    risk_level: str
    confidence_score: float
    requires_human: bool = False

@dataclass
class AgentRecommendation:
    """Agent recommendation structure"""
    agent_id: str
    agent_type: str
    action: str
    confidence: float
    reasoning: str
    risk_assessment: str
    supporting_data: Dict[str, Any]
    timestamp: datetime
    expires_at: Optional[datetime] = None

@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    step_id: str
    name: str
    agent_type: str
    conditions: Dict[str, Any]
    actions: List[str]
    timeout_seconds: int
    retry_count: int = 0
    max_retries: int = 3
    requires_human: bool = False

class WorkflowEngine:
    """Core workflow engine for managing agent handoffs and decision making"""
    
    def __init__(self, workflows_dir: str = "code/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.active_workflows: Dict[str, WorkflowContext] = {}
        self.workflow_templates: Dict[str, Any] = {}
        self.decision_trees: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, Any] = {}
        self.conflict_resolution_rules: Dict[str, Any] = {}
        self.escalation_rules: Dict[str, Any] = {}
        self.setup_logging()
        self.load_templates()
    
    def setup_logging(self):
        """Configure logging for workflow engine"""
        log_file = Path(self.workflows_dir) / 'workflow_engine.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_templates(self):
        """Load workflow templates and rules"""
        # Load trading scenario templates
        templates_dir = self.workflows_dir / 'templates'
        for template_file in templates_dir.glob('*.json'):
            with open(template_file) as f:
                template = json.load(f)
                self.workflow_templates[template['id']] = template
        
        # Load decision trees
        decision_dir = self.workflows_dir / 'decision_trees'
        for tree_file in decision_dir.glob('*.json'):
            with open(tree_file) as f:
                tree = json.load(f)
                self.decision_trees[tree['id']] = tree
        
        # Load conflict resolution rules
        conflict_file = self.workflows_dir / 'conflict_resolution' / 'rules.json'
        if conflict_file.exists():
            with open(conflict_file) as f:
                self.conflict_resolution_rules = json.load(f)
        
        # Load escalation rules
        escalation_file = self.workflows_dir / 'escalation' / 'rules.json'
        if escalation_file.exists():
            with open(escalation_file) as f:
                self.escalation_rules = json.load(f)
    
    def create_workflow(self, scenario_type: str, initial_data: Dict[str, Any], 
                       priority: int = 1, risk_level: str = "medium") -> str:
        """Create a new workflow instance"""
        workflow_id = str(uuid.uuid4())
        
        # Get workflow template
        template = self.workflow_templates.get(scenario_type)
        if not template:
            raise ValueError(f"No template found for scenario type: {scenario_type}")
        
        # Create workflow context
        context = WorkflowContext(
            workflow_id=workflow_id,
            scenario_type=scenario_type,
            current_agent=None,
            previous_agents=[],
            data=initial_data,
            metadata={
                'template_version': template.get('version', '1.0'),
                'created_by': 'system',
                'business_rules': template.get('business_rules', {})
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            priority=priority,
            risk_level=risk_level,
            confidence_score=0.0
        )
        
        self.active_workflows[workflow_id] = context
        self.logger.info(f"Created workflow {workflow_id} for scenario {scenario_type}")
        
        return workflow_id
    
    def get_workflow_context(self, workflow_id: str) -> Optional[WorkflowContext]:
        """Retrieve workflow context"""
        return self.active_workflows.get(workflow_id)
    
    def update_context(self, workflow_id: str, updates: Dict[str, Any]) -> bool:
        """Update workflow context with new data"""
        if workflow_id not in self.active_workflows:
            return False
        
        context = self.active_workflows[workflow_id]
        context.updated_at = datetime.utcnow()
        
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.data[key] = value
        
        self.logger.info(f"Updated context for workflow {workflow_id}")
        return True
    
    def handoff_to_agent(self, workflow_id: str, agent_type: str, 
                        agent_id: str, context_data: Dict[str, Any]) -> bool:
        """Handle agent handoff with context preservation"""
        if workflow_id not in self.active_workflows:
            return False
        
        context = self.active_workflows[workflow_id]
        
        # Add current agent to previous agents list
        if context.current_agent:
            context.previous_agents.append(context.current_agent)
        
        # Update current agent
        context.current_agent = f"{agent_type}:{agent_id}"
        context.updated_at = datetime.utcnow()
        
        # Update data
        context.data.update(context_data)
        
        # Apply decision tree logic
        decision = self.evaluate_decision_tree(workflow_id, context)
        
        self.logger.info(f"Handed off workflow {workflow_id} to {context.current_agent}")
        return True
    
    def evaluate_decision_tree(self, workflow_id: str, context: WorkflowContext) -> DecisionType:
        """Evaluate decision tree for routing decisions"""
        scenario_tree = self.decision_trees.get(context.scenario_type)
        if not scenario_tree:
            return DecisionType.AUTOMATED
        
        # Navigate decision tree based on context
        current_node = scenario_tree['root']
        
        while current_node.get('type') == 'condition':
            condition_met = self.evaluate_condition(current_node, context)
            next_node_id = current_node['true_branch'] if condition_met else current_node['false_branch']
            current_node = scenario_tree['nodes'].get(next_node_id, {})
        
        # Map node type to decision type
        node_type = current_node.get('type', 'automated')
        decision_map = {
            'automated': DecisionType.AUTOMATED,
            'human_required': DecisionType.HUMAN_REQUIRED,
            'escalated': DecisionType.ESCALATED,
            'conflict_resolution': DecisionType.CONFLICT_RESOLUTION
        }
        
        return decision_map.get(node_type, DecisionType.AUTOMATED)
    
    def evaluate_condition(self, condition_node: Dict[str, Any], context: WorkflowContext) -> bool:
        """Evaluate a single condition in decision tree"""
        field = condition_node['field']
        operator = condition_node['operator']
        value = condition_node['value']
        
        # Get field value from context
        if field.startswith('data.'):
            field_value = context.data.get(field[5:])
        elif field.startswith('metadata.'):
            field_value = context.metadata.get(field[9:])
        else:
            field_value = getattr(context, field, None)
        
        # Evaluate operator
        if operator == 'equals':
            return field_value == value
        elif operator == 'greater_than':
            return field_value > value
        elif operator == 'less_than':
            return field_value < value
        elif operator == 'contains':
            return value in str(field_value)
        elif operator == 'in':
            return field_value in value
        
        return False
    
    def register_agent_recommendation(self, workflow_id: str, recommendation: AgentRecommendation) -> bool:
        """Register agent recommendation for conflict resolution"""
        if workflow_id not in self.active_workflows:
            return False
        
        context = self.active_workflows[workflow_id]
        if 'recommendations' not in context.data:
            context.data['recommendations'] = []
        
        context.data['recommendations'].append(asdict(recommendation))
        context.updated_at = datetime.utcnow()
        
        self.logger.info(f"Registered recommendation from {recommendation.agent_id} for workflow {workflow_id}")
        return True
    
    def check_conflicts(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Check for conflicting recommendations"""
        if workflow_id not in self.active_workflows:
            return []
        
        context = self.active_workflows[workflow_id]
        recommendations = context.data.get('recommendations', [])
        
        conflicts = []
        
        # Check for conflicting actions
        for i, rec1 in enumerate(recommendations):
            for j, rec2 in enumerate(recommendations[i+1:], i+1):
                if rec1['action'] != rec2['action']:
                    # Check if this is a significant conflict
                    conflict_severity = self.assess_conflict_severity(rec1, rec2, self.conflict_resolution_rules)
                    if conflict_severity > 0.5:  # Threshold for significant conflict
                        conflicts.append({
                            'workflow_id': workflow_id,
                            'recommendation_1': rec1,
                            'recommendation_2': rec2,
                            'severity': conflict_severity,
                            'requires_resolution': conflict_severity > 0.8
                        })
        
        return conflicts
    
    def assess_conflict_severity(self, rec1: Dict[str, Any], rec2: Dict[str, Any], 
                               rules: Dict[str, Any]) -> float:
        """Assess severity of conflict between recommendations"""
        severity = 0.0
        
        # Action conflict
        if rec1['action'] != rec2['action']:
            severity += 0.3
        
        # Confidence difference
        conf_diff = abs(rec1['confidence'] - rec2['confidence'])
        severity += conf_diff * 0.2
        
        # Agent type hierarchy (if defined in rules)
        agent_hierarchy = rules.get('agent_hierarchy', {})
        if rec1['agent_type'] in agent_hierarchy and rec2['agent_type'] in agent_hierarchy:
            hierarchy_diff = abs(agent_hierarchy[rec1['agent_type']] - agent_hierarchy[rec2['agent_type']])
            severity += hierarchy_diff * 0.1
        
        # Risk level conflict
        if rec1['risk_assessment'] != rec2['risk_assessment']:
            severity += 0.2
        
        return min(severity, 1.0)
    
    def should_escalate(self, workflow_id: str) -> bool:
        """Check if workflow should be escalated"""
        context = self.active_workflows.get(workflow_id)
        if not context or not self.escalation_rules:
            return False
        
        # Check risk level escalation
        risk_thresholds = self.escalation_rules.get('risk_thresholds', {})
        if context.risk_level in risk_thresholds:
            required_priority = risk_thresholds[context.risk_level]
            if context.priority >= required_priority:
                return True
        
        # Check conflict escalation
        conflicts = self.check_conflicts(workflow_id)
        severe_conflicts = [c for c in conflicts if c['requires_resolution']]
        if severe_conflicts:
            return True
        
        # Check time-based escalation
        time_thresholds = self.escalation_rules.get('time_thresholds', {})
        if time_thresholds:
            elapsed = datetime.utcnow() - context.created_at
            max_time = timedelta(seconds=time_thresholds.get('max_workflow_duration', 3600))
            if elapsed > max_time:
                return True
        
        return False
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get comprehensive workflow status"""
        context = self.active_workflows.get(workflow_id)
        if not context:
            return {}
        
        status = asdict(context)
        status['conflicts'] = self.check_conflicts(workflow_id)
        status['should_escalate'] = self.should_escalate(workflow_id)
        status['decision_type'] = self.evaluate_decision_tree(workflow_id, context)
        
        return status
    
    def cleanup_workflow(self, workflow_id: str, final_state: WorkflowState):
        """Clean up completed/failed workflow"""
        if workflow_id in self.active_workflows:
            context = self.active_workflows[workflow_id]
            self.logger.info(f"Cleaning up workflow {workflow_id} with state {final_state.value}")
            
            # Archive workflow data if needed
            self.archive_workflow(workflow_id, context, final_state)
            
            # Remove from active workflows
            del self.active_workflows[workflow_id]
    
    def archive_workflow(self, workflow_id: str, context: WorkflowContext, final_state: WorkflowState):
        """Archive workflow data for compliance and analytics"""
        archive_dir = self.workflows_dir / 'archive'
        archive_dir.mkdir(exist_ok=True)
        
        archive_data = {
            'workflow_id': workflow_id,
            'final_state': final_state.value,
            'context': asdict(context),
            'archived_at': datetime.utcnow().isoformat()
        }
        
        archive_file = archive_dir / f"{workflow_id}.json"
        with open(archive_file, 'w') as f:
            json.dump(archive_data, f, indent=2, default=str)
    
    def get_performance_metrics(self, time_period: str = '24h') -> Dict[str, Any]:
        """Get workflow performance metrics"""
        # Calculate metrics from archived workflows
        archive_dir = self.workflows_dir / 'archive'
        if not archive_dir.exists():
            return {}
        
        metrics = {
            'total_workflows': 0,
            'completed_workflows': 0,
            'failed_workflows': 0,
            'avg_duration': 0,
            'agent_performance': {},
            'conflict_rate': 0,
            'escalation_rate': 0
        }
        
        # Aggregate metrics from archive files
        for archive_file in archive_dir.glob('*.json'):
            with open(archive_file) as f:
                workflow_data = json.load(f)
                
                # Apply time period filter if specified
                archived_at = datetime.fromisoformat(workflow_data['archived_at'])
                if time_period == '24h':
                    if (datetime.utcnow() - archived_at).days > 1:
                        continue
                
                metrics['total_workflows'] += 1
                
                if workflow_data['final_state'] == 'completed':
                    metrics['completed_workflows'] += 1
                elif workflow_data['final_state'] == 'failed':
                    metrics['failed_workflows'] += 1
        
        # Calculate rates
        if metrics['total_workflows'] > 0:
            metrics['conflict_rate'] = metrics['failed_workflows'] / metrics['total_workflows']
            metrics['success_rate'] = metrics['completed_workflows'] / metrics['total_workflows']
        
        return metrics