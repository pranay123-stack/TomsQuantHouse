"""
Workflow Management Tools
Comprehensive management interface for the agent handoff and decision-making workflow system
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from pathlib import Path
import argparse
import sys

# Import workflow system components
from base_engine import WorkflowEngine, WorkflowState, AgentRecommendation
from protocols.handoff_manager import AgentHandoffManager, HandoffMethod
from performance.performance_tracker import AgentPerformanceTracker
from conflict_resolution.conflict_engine import ConflictResolutionEngine, ConflictType
from escalation.escalation_manager import EscalationManager, EscalationTrigger
from versioning.version_manager import WorkflowVersionManager, RollbackReason

class WorkflowManager:
    """Main management interface for workflow system"""
    
    def __init__(self, workflows_dir: str = "code/workflows"):
        self.workflows_dir = workflows_dir
        self.workflow_engine = WorkflowEngine(workflows_dir)
        self.handoff_manager = AgentHandoffManager(workflows_dir)
        self.performance_tracker = AgentPerformanceTracker(workflows_dir)
        self.conflict_engine = ConflictResolutionEngine(workflows_dir)
        self.escalation_manager = EscalationManager(workflows_dir)
        self.version_manager = WorkflowVersionManager(workflows_dir)
    
    def create_workflow_scenario(self, scenario_type: str, data: Dict[str, Any],
                               priority: int = 1, risk_level: str = "medium") -> Dict[str, Any]:
        """Create a new workflow scenario"""
        
        try:
            # Create workflow
            workflow_id = self.workflow_engine.create_workflow(scenario_type, data, priority, risk_level)
            
            # Get workflow context
            context = self.workflow_engine.get_workflow_context(workflow_id)
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'scenario_type': scenario_type,
                'status': 'created',
                'context': asdict(context) if context else None,
                'message': f'Workflow {workflow_id} created successfully'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create workflow'
            }
    
    def execute_workflow_step(self, workflow_id: str, agent_type: str, agent_id: str,
                            decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow step"""
        
        try:
            # Get current workflow context
            context = self.workflow_engine.get_workflow_context(workflow_id)
            if not context:
                return {'success': False, 'error': 'Workflow not found'}
            
            # Handoff to agent
            handoff_success = self.workflow_engine.handoff_to_agent(
                workflow_id, agent_type, agent_id, decision_data
            )
            
            if not handoff_success:
                return {'success': False, 'error': 'Agent handoff failed'}
            
            # Create agent recommendation record
            recommendation = AgentRecommendation(
                agent_id=agent_id,
                agent_type=agent_type,
                action=decision_data.get('action', 'analyze'),
                confidence=decision_data.get('confidence', 0.5),
                reasoning=decision_data.get('reasoning', 'Automated analysis'),
                risk_assessment=decision_data.get('risk_assessment', 'medium'),
                supporting_data=decision_data.get('supporting_data', {}),
                timestamp=datetime.utcnow()
            )
            
            # Register recommendation
            self.workflow_engine.register_agent_recommendation(workflow_id, recommendation)
            
            # Record performance
            outcome_data = decision_data.get('outcome', {'successful': True})
            self.performance_tracker.record_agent_decision(
                agent_id, agent_type, decision_data, outcome_data, asdict(context)
            )
            
            # Check for conflicts
            conflicts = self.workflow_engine.check_conflicts(workflow_id)
            
            # Check for escalation triggers
            should_escalate = self.workflow_engine.should_escalate(workflow_id)
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'agent_id': agent_id,
                'action': recommendation.action,
                'conflicts_detected': len(conflicts),
                'escalation_required': should_escalate,
                'workflow_status': self.workflow_engine.get_workflow_status(workflow_id),
                'message': f'Step executed successfully by {agent_id}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to execute workflow step'
            }
    
    def resolve_conflicts(self, workflow_id: str) -> Dict[str, Any]:
        """Resolve conflicts in a workflow"""
        
        try:
            # Get workflow context
            context = self.workflow_engine.get_workflow_context(workflow_id)
            if not context:
                return {'success': False, 'error': 'Workflow not found'}
            
            # Get recommendations
            recommendations = context.data.get('recommendations', [])
            if len(recommendations) < 2:
                return {'success': True, 'message': 'No conflicts to resolve'}
            
            # Detect conflicts
            conflicts = self.conflict_engine.detect_conflicts(workflow_id, recommendations)
            
            if not conflicts:
                return {'success': True, 'message': 'No conflicts detected'}
            
            # Resolve conflicts
            resolution_results = []
            for conflict in conflicts:
                resolution = asyncio.run(self.conflict_engine.resolve_conflict(conflict.conflict_id))
                resolution_results.append(resolution)
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'conflicts_resolved': len(conflicts),
                'resolutions': resolution_results,
                'message': f'Resolved {len(conflicts)} conflicts'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to resolve conflicts'
            }
    
    def trigger_escalation(self, workflow_id: str, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger escalation for workflow"""
        
        try:
            trigger_type_str = trigger_data.get('trigger_type', 'low_confidence')
            trigger_type = EscalationTrigger(trigger_type_str)
            
            escalation_id = asyncio.run(
                self.escalation_manager.trigger_escalation(workflow_id, trigger_type, trigger_data)
            )
            
            if escalation_id:
                return {
                    'success': True,
                    'escalation_id': escalation_id,
                    'workflow_id': workflow_id,
                    'message': f'Escalation {escalation_id} initiated'
                }
            else:
                return {
                    'success': False,
                    'message': 'Escalation not triggered (conditions not met)'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to trigger escalation'
            }
    
    def get_workflow_dashboard(self, workflow_id: str) -> Dict[str, Any]:
        """Get comprehensive workflow dashboard"""
        
        try:
            # Get workflow status
            workflow_status = self.workflow_engine.get_workflow_status(workflow_id)
            
            if not workflow_status:
                return {'error': 'Workflow not found'}
            
            # Get performance metrics
            context = self.workflow_engine.get_workflow_context(workflow_id)
            agents_involved = []
            
            if context:
                # Extract unique agents
                agents_involved = list(set(
                    [context.current_agent] + context.previous_agents
                ))
                agents_involved = [a for a in agents_involved if a]
            
            # Get agent performance summaries
            agent_performance = {}
            for agent in agents_involved:
                if ':' in agent:
                    agent_id = agent.split(':')[1]
                    performance_report = self.performance_tracker.get_agent_performance_report(agent_id)
                    if 'error' not in performance_report:
                        agent_performance[agent_id] = {
                            'success_rate': performance_report['success_rate'],
                            'total_decisions': performance_report['total_decisions'],
                            'avg_metrics': performance_report['average_metrics']
                        }
            
            # Get active escalations
            active_escalations = []
            for esc in self.escalation_manager.active_escalations.values():
                if esc.workflow_id == workflow_id:
                    active_escalations.append(asdict(esc))
            
            return {
                'workflow_id': workflow_id,
                'workflow_status': workflow_status,
                'agent_performance': agent_performance,
                'active_escalations': active_escalations,
                'conflicts': workflow_status.get('conflicts', []),
                'needs_attention': (
                    workflow_status.get('should_escalate', False) or
                    len(workflow_status.get('conflicts', [])) > 0 or
                    workflow_status.get('decision_type', '').value == 'human_required'
                ),
                'dashboard_generated_at': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            return {'error': f'Failed to generate dashboard: {str(e)}'}
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide overview metrics"""
        
        try:
            # Workflow metrics
            total_workflows = len(self.workflow_engine.active_workflows)
            
            # Performance metrics
            performance_metrics = self.workflow_engine.get_performance_metrics()
            
            # Handoff metrics
            handoff_metrics = self.handoff_manager.get_transfer_metrics()
            
            # Conflict metrics
            conflict_metrics = self.conflict_engine.get_conflict_metrics()
            
            # Escalation metrics
            escalation_metrics = self.escalation_manager.get_escalation_metrics()
            
            # Version metrics
            version_metrics = self.version_manager.get_version_metrics()
            
            # Get top performing agents by type
            top_agents = {}
            agent_types = ['technical_analyzer', 'risk_analyzer', 'execution_agent']
            
            for agent_type in agent_types:
                top_performers = self.performance_tracker.get_top_performing_agents(agent_type, limit=5)
                top_agents[agent_type] = top_performers
            
            return {
                'system_status': 'operational',
                'timestamp': datetime.utcnow().isoformat(),
                'workflows': {
                    'active_workflows': total_workflows,
                    'metrics': performance_metrics
                },
                'handoffs': handoff_metrics,
                'conflicts': conflict_metrics,
                'escalations': escalation_metrics,
                'versioning': version_metrics,
                'top_agents': top_agents,
                'system_health': {
                    'workflow_success_rate': performance_metrics.get('success_rate', 0),
                    'conflict_resolution_rate': 1 - conflict_metrics.get('conflict_rate', 0),
                    'escalation_rate': escalation_metrics.get('approval_rate', 0)
                }
            }
        
        except Exception as e:
            return {'error': f'Failed to get system overview: {str(e)}'}
    
    def backup_workflow_data(self, backup_path: Optional[str] = None) -> Dict[str, Any]:
        """Backup workflow system data"""
        
        try:
            if not backup_path:
                backup_path = f"workflow_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            
            backup_data = {
                'backup_timestamp': datetime.utcnow().isoformat(),
                'workflow_engine': {
                    'active_workflows': {
                        k: asdict(v) for k, v in self.workflow_engine.active_workflows.items()
                    },
                    'performance_metrics': self.workflow_engine.get_performance_metrics()
                },
                'handoff_manager': {
                    'transfer_history': self.handoff_manager.transfer_history[-100:]  # Last 100
                },
                'performance_tracker': {
                    'performance_history': {
                        k: [asdict(snapshot) for snapshot in list(v)[-50:]]  # Last 50 per agent
                        for k, v in self.performance_tracker.performance_history.items()
                    }
                },
                'escalation_manager': {
                    'escalation_history': [asdict(e) for e in self.escalation_manager.escalation_history[-50:]]
                },
                'versioning': version_metrics
            }
            
            # Save backup
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            return {
                'success': True,
                'backup_path': backup_path,
                'backup_size_mb': Path(backup_path).stat().st_size / (1024 * 1024),
                'message': f'Backup created successfully at {backup_path}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create backup'
            }
    
    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old workflow data"""
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Clean up archived workflows
            archive_dir = Path(self.workflows_dir) / 'archive'
            if archive_dir.exists():
                removed_files = 0
                for file_path in archive_dir.glob('*.json'):
                    file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_date < cutoff_date:
                        file_path.unlink()
                        removed_files += 1
            
            # Clean up old transfer history
            original_count = len(self.handoff_manager.transfer_history)
            self.handoff_manager.transfer_history = [
                t for t in self.handoff_manager.transfer_history
                if datetime.fromisoformat(t['timestamp']) > cutoff_date
            ]
            cleaned_handoffs = original_count - len(self.handoff_manager.transfer_history)
            
            return {
                'success': True,
                'cutoff_date': cutoff_date.isoformat(),
                'removed_files': removed_files,
                'cleaned_handoffs': cleaned_handoffs,
                'message': f'Cleaned up {removed_files} files and {cleaned_handoffs} handoffs'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to cleanup old data'
            }

def main():
    """Main CLI interface for workflow management"""
    
    parser = argparse.ArgumentParser(description='Workflow Management System')
    parser.add_argument('--workflows-dir', default='code/workflows', help='Workflows directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create workflow
    create_parser = subparsers.add_parser('create', help='Create new workflow')
    create_parser.add_argument('scenario_type', help='Scenario type (e.g., high_confidence_prediction)')
    create_parser.add_argument('--data', help='JSON data for workflow')
    create_parser.add_argument('--priority', type=int, default=1, help='Priority level')
    create_parser.add_argument('--risk-level', default='medium', help='Risk level')
    
    # Execute step
    execute_parser = subparsers.add_parser('execute', help='Execute workflow step')
    execute_parser.add_argument('workflow_id', help='Workflow ID')
    execute_parser.add_argument('agent_type', help='Agent type')
    execute_parser.add_argument('agent_id', help='Agent ID')
    execute_parser.add_argument('--decision-data', help='JSON decision data')
    
    # Dashboard
    dashboard_parser = subparsers.add_parser('dashboard', help='Get workflow dashboard')
    dashboard_parser.add_argument('workflow_id', help='Workflow ID')
    
    # System overview
    subparsers.add_parser('overview', help='Get system overview')
    
    # Resolve conflicts
    conflicts_parser = subparsers.add_parser('conflicts', help='Resolve conflicts')
    conflicts_parser.add_argument('workflow_id', help='Workflow ID')
    
    # Trigger escalation
    escalate_parser = subparsers.add_parser('escalate', help='Trigger escalation')
    escalate_parser.add_argument('workflow_id', help='Workflow ID')
    escalate_parser.add_argument('trigger_type', help='Trigger type')
    
    # Backup
    backup_parser = subparsers.add_parser('backup', help='Backup workflow data')
    backup_parser.add_argument('--path', help='Backup file path')
    
    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old data')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Days old for cleanup')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = WorkflowManager(args.workflows_dir)
    
    try:
        if args.command == 'create':
            data = json.loads(args.data) if args.data else {}
            result = manager.create_workflow_scenario(
                args.scenario_type, data, args.priority, args.risk_level
            )
            print(json.dumps(result, indent=2))
        
        elif args.command == 'execute':
            decision_data = json.loads(args.decision_data) if args.decision_data else {}
            result = manager.execute_workflow_step(
                args.workflow_id, args.agent_type, args.agent_id, decision_data
            )
            print(json.dumps(result, indent=2))
        
        elif args.command == 'dashboard':
            result = manager.get_workflow_dashboard(args.workflow_id)
            print(json.dumps(result, indent=2))
        
        elif args.command == 'overview':
            result = manager.get_system_overview()
            print(json.dumps(result, indent=2))
        
        elif args.command == 'conflicts':
            result = manager.resolve_conflicts(args.workflow_id)
            print(json.dumps(result, indent=2))
        
        elif args.command == 'escalate':
            trigger_data = {'trigger_type': args.trigger_type}
            result = manager.trigger_escalation(args.workflow_id, trigger_data)
            print(json.dumps(result, indent=2))
        
        elif args.command == 'backup':
            result = manager.backup_workflow_data(args.path)
            print(json.dumps(result, indent=2))
        
        elif args.command == 'cleanup':
            result = manager.cleanup_old_data(args.days)
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()