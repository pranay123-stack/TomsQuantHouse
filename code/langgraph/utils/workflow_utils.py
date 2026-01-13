"""
Workflow Utilities
Utility functions and helpers for the LangGraph workflow system
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
import statistics
import uuid

from ..workflows.state import WorkflowState, WorkflowStatus, DecisionOutcome, RiskLevel

logger = logging.getLogger(__name__)

class WorkflowUtils:
    """Utility functions for workflow management and analysis"""
    
    @staticmethod
    def validate_workflow_state(state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate workflow state structure
        
        Args:
            state: Workflow state dictionary
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        required_fields = [
            "workflow_id", "execution_id", "status", "start_time", 
            "current_node", "metadata"
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in state:
                errors.append(f"Missing required field: {field}")
        
        # Validate status
        if "status" in state:
            valid_statuses = [s.value for s in WorkflowStatus]
            if state["status"] not in valid_statuses:
                errors.append(f"Invalid status: {state['status']}")
        
        # Validate timestamps
        for timestamp_field in ["start_time", "end_time", "last_checkpoint_time"]:
            if timestamp_field in state and state[timestamp_field]:
                try:
                    datetime.fromisoformat(state[timestamp_field])
                except ValueError:
                    errors.append(f"Invalid timestamp format: {timestamp_field}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def format_workflow_summary(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a formatted summary of workflow state
        
        Args:
            state: Workflow state dictionary
            
        Returns:
            Dict[str, Any]: Formatted summary
        """
        try:
            summary = {
                "workflow_id": state.get("workflow_id", "unknown"),
                "status": state.get("status", "unknown"),
                "symbol": state.get("metadata", {}).get("symbol", "unknown"),
                "strategy": state.get("metadata", {}).get("strategy", "unknown"),
                "current_node": state.get("current_node", "unknown"),
                "execution_time": None,
                "progress": 0
            }
            
            # Calculate execution time
            start_time = state.get("start_time")
            end_time = state.get("end_time")
            
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    if end_time:
                        end_dt = datetime.fromisoformat(end_time)
                        summary["execution_time"] = (end_dt - start_dt).total_seconds()
                    else:
                        # Still running
                        summary["execution_time"] = (datetime.now() - start_dt).total_seconds()
                except Exception:
                    pass
            
            # Calculate progress based on current node
            node_progress = {
                "": 0,
                "market_analysis": 25,
                "ml_prediction": 50,
                "risk_management": 75,
                "execution": 90,
                "completion": 100,
                "error_handling": 100
            }
            
            current_node = state.get("current_node", "")
            summary["progress"] = node_progress.get(current_node, 0)
            
            # Add decision info if available
            if state.get("ml_prediction"):
                ml_prediction = state["ml_prediction"]
                if isinstance(ml_prediction, dict):
                    summary["predicted_decision"] = ml_prediction.get("decision")
                    summary["confidence"] = ml_prediction.get("confidence")
            
            # Add risk info if available
            if state.get("risk_assessment"):
                risk_assessment = state["risk_assessment"]
                if isinstance(risk_assessment, dict):
                    summary["risk_level"] = risk_assessment.get("risk_level")
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to format workflow summary: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def calculate_workflow_statistics(workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for a list of workflows
        
        Args:
            workflows: List of workflow data
            
        Returns:
            Dict[str, Any]: Statistical summary
        """
        if not workflows:
            return {
                "total_count": 0,
                "status_distribution": {},
                "average_execution_time": 0,
                "success_rate": 0,
                "error_rate": 0
            }
        
        # Status distribution
        status_counts = {}
        execution_times = []
        error_workflows = 0
        
        for workflow in workflows:
            status = workflow.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if status == "failed":
                error_workflows += 1
            
            # Calculate execution time if possible
            try:
                start_time = workflow.get("start_time")
                end_time = workflow.get("end_time")
                
                if start_time and end_time:
                    start_dt = datetime.fromisoformat(start_time)
                    end_dt = datetime.fromisoformat(end_time)
                    execution_time = (end_dt - start_dt).total_seconds()
                    execution_times.append(execution_time)
            except Exception:
                continue
        
        # Calculate statistics
        total_count = len(workflows)
        completed_count = status_counts.get("completed", 0)
        success_rate = completed_count / total_count if total_count > 0 else 0
        error_rate = error_workflows / total_count if total_count > 0 else 0
        
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0
        median_execution_time = statistics.median(execution_times) if execution_times else 0
        
        return {
            "total_count": total_count,
            "status_distribution": status_counts,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "average_execution_time": avg_execution_time,
            "median_execution_time": median_execution_time,
            "min_execution_time": min(execution_times) if execution_times else 0,
            "max_execution_time": max(execution_times) if execution_times else 0,
            "execution_time_std": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        }
    
    @staticmethod
    def export_workflow_data(
        workflow_id: str, 
        state: Dict[str, Any], 
        format_type: str = "json"
    ) -> Union[str, Dict[str, Any]]:
        """
        Export workflow data in various formats
        
        Args:
            workflow_id: Workflow identifier
            state: Workflow state data
            format_type: Export format ("json", "yaml", "csv")
            
        Returns:
            Union[str, Dict[str, Any]]: Exported data
        """
        try:
            if format_type.lower() == "json":
                return json.dumps(state, indent=2, default=str)
            
            elif format_type.lower() == "yaml":
                import yaml
                return yaml.dump(state, default_flow_style=False)
            
            elif format_type.lower() == "csv":
                # Convert to CSV format (flattened)
                flattened = WorkflowUtils._flatten_workflow_state(state)
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=flattened.keys())
                writer.writeheader()
                writer.writerow(flattened)
                
                return output.getvalue()
            
            else:
                raise ValueError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error(f"Failed to export workflow data: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _flatten_workflow_state(state: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested workflow state for CSV export"""
        flattened = {}
        
        def flatten_dict(d, parent_key=""):
            for key, value in d.items():
                new_key = f"{parent_key}_{key}" if parent_key else key
                if isinstance(value, dict):
                    flatten_dict(value, new_key)
                elif isinstance(value, list):
                    flattened[new_key] = json.dumps(value)
                else:
                    flattened[new_key] = value
        
        flatten_dict(state)
        return flattened
    
    @staticmethod
    def generate_workflow_report(
        workflows: List[Dict[str, Any]], 
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate comprehensive workflow report
        
        Args:
            workflows: List of workflow data
            time_range_hours: Time range for report
            
        Returns:
            Dict[str, Any]: Comprehensive report
        """
        try:
            # Filter by time range
            cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
            filtered_workflows = []
            
            for workflow in workflows:
                try:
                    workflow_time = datetime.fromisoformat(workflow.get("start_time", ""))
                    if workflow_time >= cutoff_time:
                        filtered_workflows.append(workflow)
                except Exception:
                    continue
            
            # Calculate statistics
            stats = WorkflowUtils.calculate_workflow_statistics(filtered_workflows)
            
            # Identify trends and patterns
            trends = WorkflowUtils._analyze_workflow_trends(filtered_workflows)
            
            # Generate recommendations
            recommendations = WorkflowUtils._generate_workflow_recommendations(stats, trends)
            
            return {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "time_range_hours": time_range_hours,
                    "total_workflows_analyzed": len(filtered_workflows)
                },
                "statistics": stats,
                "trends": trends,
                "recommendations": recommendations,
                "workflows": filtered_workflows[:10]  # Include sample of workflows
            }
            
        except Exception as e:
            logger.error(f"Failed to generate workflow report: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _analyze_workflow_trends(workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in workflow data"""
        if not workflows:
            return {}
        
        trends = {
            "hourly_distribution": {},
            "node_performance": {},
            "symbol_performance": {},
            "strategy_performance": {}
        }
        
        # Hourly distribution
        for workflow in workflows:
            try:
                start_time = datetime.fromisoformat(workflow.get("start_time", ""))
                hour = start_time.hour
                trends["hourly_distribution"][hour] = trends["hourly_distribution"].get(hour, 0) + 1
            except Exception:
                continue
        
        # Node performance (simplified)
        # This would need actual execution data to calculate properly
        node_success_rates = {
            "market_analysis": 0.95,
            "ml_prediction": 0.90,
            "risk_management": 0.85,
            "execution": 0.80,
            "completion": 0.95
        }
        trends["node_performance"] = node_success_rates
        
        # Symbol performance
        symbol_stats = {}
        for workflow in workflows:
            symbol = workflow.get("metadata", {}).get("symbol", "unknown")
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {"total": 0, "successful": 0}
            
            symbol_stats[symbol]["total"] += 1
            if workflow.get("status") == "completed":
                symbol_stats[symbol]["successful"] += 1
        
        for symbol, stats in symbol_stats.items():
            stats["success_rate"] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
        
        trends["symbol_performance"] = symbol_stats
        
        return trends
    
    @staticmethod
    def _generate_workflow_recommendations(
        stats: Dict[str, Any], 
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on statistics and trends"""
        recommendations = []
        
        # Performance recommendations
        if stats.get("success_rate", 0) < 0.9:
            recommendations.append("Improve workflow success rate through better error handling")
        
        if stats.get("average_execution_time", 0) > 300:  # 5 minutes
            recommendations.append("Optimize workflow execution time")
        
        # Trend-based recommendations
        hourly_dist = trends.get("hourly_distribution", {})
        if hourly_dist:
            peak_hours = [h for h, count in hourly_dist.items() if count > max(hourly_dist.values()) * 0.8]
            if peak_hours:
                recommendations.append(f"Consider scaling during peak hours: {peak_hours}")
        
        # Node performance recommendations
        node_perf = trends.get("node_performance", {})
        for node, rate in node_perf.items():
            if rate < 0.8:
                recommendations.append(f"Optimize {node} node performance")
        
        # General recommendations
        recommendations.extend([
            "Implement regular workflow health monitoring",
            "Consider batching similar workflows for efficiency",
            "Review and update risk management parameters",
            "Implement workflow priority queuing"
        ])
        
        return recommendations
    
    @staticmethod
    def create_workflow_template(
        template_name: str,
        base_workflow: Dict[str, Any],
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a workflow template from an existing workflow
        
        Args:
            template_name: Name for the template
            base_workflow: Base workflow to create template from
            overrides: Optional overrides for the template
            
        Returns:
            Dict[str, Any]: Workflow template
        """
        try:
            template = {
                "template_name": template_name,
                "created_at": datetime.now().isoformat(),
                "base_workflow": base_workflow,
                "default_parameters": {
                    "symbol": "BTCUSDT",
                    "strategy": "default",
                    "auto_checkpoint": True,
                    "max_execution_time": 1800
                },
                "required_fields": ["symbol", "strategy"],
                "optional_fields": ["metadata", "callback_url"]
            }
            
            # Apply overrides
            if overrides:
                template["default_parameters"].update(overrides)
            
            return template
            
        except Exception as e:
            logger.error(f"Failed to create workflow template: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def validate_workflow_template(template: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate workflow template structure
        
        Args:
            template: Template to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        required_fields = ["template_name", "default_parameters", "required_fields"]
        
        for field in required_fields:
            if field not in template:
                errors.append(f"Missing required field: {field}")
        
        # Validate required fields structure
        required_fields_list = template.get("required_fields", [])
        default_params = template.get("default_parameters", {})
        
        for field in required_fields_list:
            if field not in default_params:
                errors.append(f"Required field '{field}' not in default_parameters")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def merge_workflow_states(
        primary: Dict[str, Any], 
        secondary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two workflow states with conflict resolution
        
        Args:
            primary: Primary state (takes precedence)
            secondary: Secondary state
            
        Returns:
            Dict[str, Any]: Merged state
        """
        try:
            merged = primary.copy()
            
            # Merge specific fields
            for key, value in secondary.items():
                if key not in merged:
                    merged[key] = value
                elif key in ["metadata", "execution_history"]:
                    # Merge dictionaries and lists
                    if isinstance(value, dict) and isinstance(merged[key], dict):
                        merged[key].update(value)
                    elif isinstance(value, list) and isinstance(merged[key], list):
                        merged[key].extend(value)
            
            # Handle timestamp conflicts
            for timestamp_field in ["start_time", "end_time"]:
                if timestamp_field in secondary and timestamp_field not in merged:
                    merged[timestamp_field] = secondary[timestamp_field]
            
            return merged
            
        except Exception as e:
            logger.error(f"Failed to merge workflow states: {e}")
            return primary
    
    @staticmethod
    def generate_workflow_id(
        symbol: str, 
        strategy: str, 
        prefix: str = "trading"
    ) -> str:
        """
        Generate a consistent workflow ID
        
        Args:
            symbol: Trading symbol
            strategy: Trading strategy
            prefix: ID prefix
            
        Returns:
            str: Generated workflow ID
        """
        timestamp = int(datetime.now().timestamp())
        unique_id = str(uuid.uuid4())[:8]
        
        return f"{prefix}_{symbol}_{strategy}_{timestamp}_{unique_id}"
    
    @staticmethod
    def parse_workflow_id(workflow_id: str) -> Optional[Dict[str, str]]:
        """
        Parse workflow ID to extract components
        
        Args:
            workflow_id: Workflow ID to parse
            
        Returns:
            Optional[Dict[str, str]]: Parsed components or None if parsing fails
        """
        try:
            parts = workflow_id.split("_")
            if len(parts) < 4:
                return None
            
            return {
                "prefix": parts[0],
                "symbol": parts[1],
                "strategy": parts[2],
                "timestamp": parts[3],
                "unique_id": parts[4] if len(parts) > 4 else ""
            }
            
        except Exception:
            return None
    
    @staticmethod
    def estimate_workflow_cost(
        execution_time: float,
        nodes_executed: int,
        checkpoint_count: int
    ) -> Dict[str, float]:
        """
        Estimate workflow execution cost
        
        Args:
            execution_time: Total execution time in seconds
            nodes_executed: Number of nodes executed
            checkpoint_count: Number of checkpoints created
            
        Returns:
            Dict[str, float]: Cost breakdown
        """
        # Example cost model (these would be actual costs in production)
        costs = {
            "execution_cost": execution_time * 0.001,  # $0.001 per second
            "node_cost": nodes_executed * 0.01,       # $0.01 per node
            "checkpoint_cost": checkpoint_count * 0.005,  # $0.005 per checkpoint
            "total_cost": 0
        }
        
        costs["total_cost"] = sum([
            costs["execution_cost"],
            costs["node_cost"],
            costs["checkpoint_cost"]
        ])
        
        return costs
    
    @staticmethod
    def convert_state_to_dict(state: Union[Dict, object]) -> Dict[str, Any]:
        """
        Convert workflow state object to dictionary
        
        Args:
            state: State object or dictionary
            
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        if isinstance(state, dict):
            return state
        
        if hasattr(state, '__dict__'):
            return {
                k: WorkflowUtils.convert_state_to_dict(v) 
                for k, v in state.__dict__.items()
            }
        
        return {"value": state}