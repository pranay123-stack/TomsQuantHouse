"""
Workflow Visualization and Monitoring Tools
Provides comprehensive visualization and monitoring capabilities for LangGraph workflows
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import asdict
import statistics

from ..checkpoints.redis_checkpointer import RedisCheckpointer

logger = logging.getLogger(__name__)

class WorkflowVisualization:
    """Tools for visualizing workflow execution and state"""
    
    def __init__(self, redis_checkpointer: RedisCheckpointer):
        """
        Initialize workflow visualization
        
        Args:
            redis_checkpointer: Redis checkpointer for accessing workflow data
        """
        self.redis_checkpointer = redis_checkpointer
    
    def generate_workflow_graph_mermaid(
        self, 
        workflow_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None
    ) -> str:
        """
        Generate Mermaid diagram for workflow execution graph
        
        Args:
            workflow_id: Specific workflow to visualize
            checkpoint_id: Specific checkpoint to visualize
            
        Returns:
            str: Mermaid diagram code
        """
        try:
            # Base workflow graph structure
            mermaid_code = """
            graph TD
                Start([Workflow Start]) --> MarketAnalysis[Market Analysis]
                MarketAnalysis --> MLPrediction[ML Prediction]
                MLPrediction --> RiskManagement[Risk Management]
                RiskManagement -->|Low Risk| Execution[Execution]
                RiskManagement -->|High Risk| RiskReview[Risk Review]
                RiskReview --> RiskManagement
                Execution --> Completion([Workflow Complete])
                RiskManagement -->|Critical Risk| ErrorHandling[Error Handling]
                MarketAnalysis --> ErrorHandling
                MLPrediction --> ErrorHandling
                ErrorHandling --> Completion
            """
            
            # If specific workflow provided, add execution path
            if workflow_id or checkpoint_id:
                execution_path = self._get_execution_path(workflow_id, checkpoint_id)
                if execution_path:
                    # Add highlighted execution path
                    mermaid_code += self._add_execution_highlighting(execution_path)
            
            return mermaid_code
            
        except Exception as e:
            logger.error(f"Failed to generate workflow graph: {e}")
            return "graph TD\n    Error[Visualization Error]"
    
    def _get_execution_path(
        self, 
        workflow_id: Optional[str], 
        checkpoint_id: Optional[str]
    ) -> List[str]:
        """Get the actual execution path for a workflow"""
        try:
            if checkpoint_id:
                state = self.redis_checkpointer.restore_checkpoint(checkpoint_id)
                if state:
                    return state.node_history
            elif workflow_id:
                history = self.redis_checkpointer.get_workflow_history(workflow_id)
                return [entry["node_name"] for entry in history]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get execution path: {e}")
            return []
    
    def _add_execution_highlighting(self, execution_path: List[str]) -> str:
        """Add execution path highlighting to Mermaid diagram"""
        if not execution_path:
            return ""
        
        highlighting = "\n\n    %% Execution Path Highlights\n"
        
        # Add style classes
        highlighting += """
            classDef executed fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
            classDef failed fill:#ffebee,stroke:#c62828,stroke-width:2px
            classDef completed fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
        """
        
        # Highlight executed nodes
        for node in execution_path:
            if node == "market_analysis":
                highlighting += "    MarketAnalysis:::executed\n"
            elif node == "ml_prediction":
                highlighting += "    MLPrediction:::executed\n"
            elif node == "risk_management":
                highlighting += "    RiskManagement:::executed\n"
            elif node == "execution":
                highlighting += "    Execution:::executed\n"
            elif node == "error_handling":
                highlighting += "    ErrorHandling:::failed\n"
            elif node == "completion":
                highlighting += "    Completion:::completed\n"
        
        return highlighting
    
    def generate_workflow_timeline(
        self, 
        workflow_id: str
    ) -> str:
        """
        Generate timeline visualization for workflow execution
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            str: Mermaid timeline diagram
        """
        try:
            history = self.redis_checkpointer.get_workflow_history(workflow_id)
            if not history:
                return "timeline\n    title: No Execution History"
            
            timeline = "timeline\n"
            timeline += f"    title: Workflow {workflow_id} Execution Timeline\n"
            
            current_date = None
            for entry in history:
                try:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    date_str = timestamp.strftime("%Y-%m-%d")
                    
                    # Add date header if new date
                    if date_str != current_date:
                        current_date = date_str
                        timeline += f"    {date_str} : \n"
                    
                    # Add event
                    time_str = timestamp.strftime("%H:%M:%S")
                    timeline += f"        {time_str} : {entry['node_name']} ({entry['status']})\n"
                    
                except Exception as e:
                    logger.warning(f"Failed to parse timeline entry: {e}")
                    continue
            
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to generate workflow timeline: {e}")
            return "timeline\n    title: Timeline Generation Error"
    
    def generate_execution_metrics_chart(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Generate execution metrics for visualization
        
        Args:
            time_range_hours: Time range for metrics
            
        Returns:
            Dict containing chart data
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
            workflows = self.redis_checkpointer.list_workflows(limit=1000)
            
            # Filter by time range
            recent_workflows = []
            for workflow in workflows:
                try:
                    workflow_time = datetime.fromisoformat(workflow["timestamp"])
                    if workflow_time >= cutoff_time:
                        recent_workflows.append(workflow)
                except Exception:
                    continue
            
            # Calculate metrics
            total_workflows = len(recent_workflows)
            status_counts = {}
            execution_times = []
            
            for workflow in recent_workflows:
                # Status distribution
                status = workflow["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Calculate execution time if available
                try:
                    start_time = datetime.fromisoformat(workflow["timestamp"])
                    # This is a simplified calculation - in real implementation,
                    # you'd get the actual start and end times from the state
                    execution_time = 30  # Placeholder
                    execution_times.append(execution_time)
                except Exception:
                    continue
            
            # Prepare chart data
            chart_data = {
                "type": "metrics_overview",
                "time_range_hours": time_range_hours,
                "total_workflows": total_workflows,
                "status_distribution": {
                    "data": [{"status": status, "count": count} for status, count in status_counts.items()],
                    "labels": list(status_counts.keys())
                },
                "execution_times": {
                    "average": statistics.mean(execution_times) if execution_times else 0,
                    "median": statistics.median(execution_times) if execution_times else 0,
                    "min": min(execution_times) if execution_times else 0,
                    "max": max(execution_times) if execution_times else 0,
                    "data": execution_times
                }
            }
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Failed to generate execution metrics: {e}")
            return {"error": str(e)}


class WorkflowMonitoring:
    """Real-time monitoring and alerting for workflows"""
    
    def __init__(self, redis_checkpointer: RedisCheckpointer):
        """
        Initialize workflow monitoring
        
        Args:
            redis_checkpointer: Redis checkpointer for accessing workflow data
        """
        self.redis_checkpointer = redis_checkpointer
        self.alert_thresholds = self._default_alert_thresholds()
        self.monitoring_active = False
        
    def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start real-time monitoring"""
        self.monitoring_active = True
        logger.info(f"Started workflow monitoring with {interval_seconds}s interval")
    
    def stop_monitoring(self) -> None:
        """Stop real-time monitoring"""
        self.monitoring_active = False
        logger.info("Stopped workflow monitoring")
    
    def get_real_time_status(self) -> Dict[str, Any]:
        """
        Get real-time status of all workflows
        
        Returns:
            Dict containing current workflow status
        """
        try:
            workflows = self.redis_checkpointer.list_workflows(limit=1000)
            
            status_summary = {
                "total_workflows": len(workflows),
                "by_status": {},
                "alerts": [],
                "health_score": 100,
                "timestamp": datetime.now().isoformat()
            }
            
            # Categorize workflows by status
            for workflow in workflows:
                status = workflow["status"]
                if status not in status_summary["by_status"]:
                    status_summary["by_status"][status] = []
                
                status_summary["by_status"][status].append({
                    "workflow_id": workflow["workflow_id"],
                    "checkpoint_id": workflow["checkpoint_id"],
                    "timestamp": workflow["timestamp"],
                    "current_node": workflow.get("current_node", "")
                })
            
            # Check for alerts
            alerts = self._check_alert_conditions(workflows)
            status_summary["alerts"] = alerts
            
            # Calculate health score
            status_summary["health_score"] = self._calculate_health_score(workflows, alerts)
            
            return status_summary
            
        except Exception as e:
            logger.error(f"Failed to get real-time status: {e}")
            return {"error": str(e)}
    
    def get_workflow_health(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get detailed health assessment for a specific workflow
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Dict containing health metrics
        """
        try:
            # Get workflow data
            workflow_state = self._get_latest_workflow_state(workflow_id)
            history = self.redis_checkpointer.get_workflow_history(workflow_id)
            
            if not workflow_state:
                return {"status": "not_found"}
            
            # Calculate health metrics
            health_metrics = {
                "workflow_id": workflow_id,
                "overall_health": self._assess_workflow_health(workflow_state, history),
                "performance_metrics": self._calculate_performance_metrics(workflow_state, history),
                "risk_assessment": self._assess_workflow_risks(workflow_state),
                "recommendations": self._generate_health_recommendations(workflow_state, history),
                "timestamp": datetime.now().isoformat()
            }
            
            return health_metrics
            
        except Exception as e:
            logger.error(f"Failed to get workflow health for {workflow_id}: {e}")
            return {"error": str(e)}
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get comprehensive system overview"""
        try:
            # Get all workflows
            workflows = self.redis_checkpointer.list_workflows(limit=1000)
            
            # System metrics
            system_metrics = {
                "total_workflows": len(workflows),
                "active_workflows": len([w for w in workflows if w["status"] == "running"]),
                "completed_workflows": len([w for w in workflows if w["status"] == "completed"]),
                "failed_workflows": len([w for w in workflows if w["status"] == "failed"]),
                "system_health": "healthy",
                "timestamp": datetime.now().isoformat()
            }
            
            # Performance metrics
            performance_metrics = self._calculate_system_performance_metrics(workflows)
            
            # Resource utilization
            resource_utilization = self._calculate_resource_utilization()
            
            # Recent alerts
            recent_alerts = self._get_recent_alerts(workflows)
            
            return {
                "system_metrics": system_metrics,
                "performance": performance_metrics,
                "resources": resource_utilization,
                "alerts": recent_alerts,
                "recommendations": self._generate_system_recommendations(system_metrics, performance_metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to get system overview: {e}")
            return {"error": str(e)}
    
    def _default_alert_thresholds(self) -> Dict[str, float]:
        """Default alert thresholds"""
        return {
            "failure_rate": 0.10,          # 10% failure rate threshold
            "avg_execution_time": 300,      # 5 minutes average execution time
            "stale_workflow_hours": 2,      # 2 hours for stale workflows
            "memory_usage": 0.80,           # 80% memory usage
            "active_workflow_limit": 50,     # Maximum active workflows
            "error_log_threshold": 5        # Maximum errors before alert
        }
    
    def _check_alert_conditions(self, workflows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        alerts = []
        
        # Check failure rate
        failed_count = len([w for w in workflows if w["status"] == "failed"])
        total_count = len(workflows)
        
        if total_count > 0:
            failure_rate = failed_count / total_count
            if failure_rate > self.alert_thresholds["failure_rate"]:
                alerts.append({
                    "type": "high_failure_rate",
                    "severity": "high" if failure_rate > 0.20 else "medium",
                    "message": f"Failure rate: {failure_rate:.2%}",
                    "value": failure_rate,
                    "threshold": self.alert_thresholds["failure_rate"]
                })
        
        # Check for stale workflows
        cutoff_time = datetime.now() - timedelta(hours=self.alert_thresholds["stale_workflow_hours"])
        stale_workflows = []
        
        for workflow in workflows:
            try:
                workflow_time = datetime.fromisoformat(workflow["timestamp"])
                if workflow_time < cutoff_time and workflow["status"] in ["pending", "running"]:
                    stale_workflows.append(workflow)
            except Exception:
                continue
        
        if stale_workflows:
            alerts.append({
                "type": "stale_workflows",
                "severity": "medium",
                "message": f"{len(stale_workflows)} stale workflows detected",
                "count": len(stale_workflows),
                "workflows": [w["workflow_id"] for w in stale_workflows]
            })
        
        return alerts
    
    def _calculate_health_score(self, workflows: List[Dict[str, Any]], alerts: List[Dict[str, Any]]) -> int:
        """Calculate overall system health score"""
        base_score = 100
        
        # Deduct for alerts
        for alert in alerts:
            if alert["severity"] == "high":
                base_score -= 20
            elif alert["severity"] == "medium":
                base_score -= 10
            else:
                base_score -= 5
        
        # Deduct for failure rate
        failed_count = len([w for w in workflows if w["status"] == "failed"])
        total_count = len(workflows)
        
        if total_count > 0:
            failure_rate = failed_count / total_count
            base_score -= int(failure_rate * 50)
        
        return max(0, min(100, base_score))
    
    def _get_latest_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest state for a workflow"""
        try:
            workflows = self.redis_checkpointer.list_workflows(
                status_filter=None,
                limit=100
            )
            
            for workflow in workflows:
                if workflow["workflow_id"] == workflow_id:
                    checkpoint_id = workflow["checkpoint_id"]
                    return self.redis_checkpointer.restore_checkpoint(checkpoint_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest workflow state: {e}")
            return None
    
    def _assess_workflow_health(self, workflow_state: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
        """Assess overall workflow health"""
        if not workflow_state:
            return "unknown"
        
        status = workflow_state.get("status", "unknown")
        
        if status == "completed":
            return "healthy"
        elif status == "failed":
            return "unhealthy"
        elif status == "running":
            return "active"
        elif status == "cancelled":
            return "stopped"
        else:
            return "unknown"
    
    def _calculate_performance_metrics(self, workflow_state: Dict[str, Any], history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate workflow performance metrics"""
        metrics = {
            "execution_time": 0,
            "node_count": len(history),
            "success_rate": 0,
            "avg_node_time": 0
        }
        
        if workflow_state and history:
            # Calculate execution time
            start_time = None
            end_time = None
            
            try:
                if history:
                    start_time = datetime.fromisoformat(history[0]["timestamp"])
                    end_time = datetime.fromisoformat(history[-1]["timestamp"])
                    metrics["execution_time"] = (end_time - start_time).total_seconds()
                
                # Calculate success rate
                successful_nodes = len([h for h in history if h["status"] == "success"])
                metrics["success_rate"] = successful_nodes / len(history) if history else 0
                
                # Calculate average node execution time
                if metrics["execution_time"] > 0:
                    metrics["avg_node_time"] = metrics["execution_time"] / metrics["node_count"]
                
            except Exception as e:
                logger.warning(f"Failed to calculate performance metrics: {e}")
        
        return metrics
    
    def _assess_workflow_risks(self, workflow_state: Dict[str, Any]) -> List[str]:
        """Assess risks for a workflow"""
        risks = []
        
        if not workflow_state:
            return ["Unknown workflow state"]
        
        status = workflow_state.get("status")
        
        if status == "running":
            # Check for long-running workflows
            start_time_str = workflow_state.get("start_time")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    runtime = (datetime.now() - start_time).total_seconds()
                    if runtime > 1800:  # 30 minutes
                        risks.append("Long-running workflow")
                except Exception:
                    pass
        
        # Check error log
        error_log = workflow_state.get("error_log", [])
        if len(error_log) > 5:
            risks.append("High error count")
        
        # Check if risk assessment indicates high risk
        risk_assessment = workflow_state.get("risk_assessment")
        if risk_assessment and isinstance(risk_assessment, dict):
            risk_level = risk_assessment.get("risk_level")
            if risk_level in ["high", "critical"]:
                risks.append(f"High risk level: {risk_level}")
        
        return risks
    
    def _generate_health_recommendations(self, workflow_state: Dict[str, Any], history: List[Dict[str, Any]]) -> List[str]:
        """Generate health recommendations for a workflow"""
        recommendations = []
        
        if not workflow_state:
            return ["Investigate workflow state retrieval issues"]
        
        status = workflow_state.get("status")
        
        if status == "failed":
            recommendations.append("Review error logs and checkpoint data")
            recommendations.append("Consider workflow restart with improved error handling")
        elif status == "running":
            recommendations.append("Monitor execution progress")
            recommendations.append("Consider timeout limits for long-running workflows")
        elif status == "cancelled":
            recommendations.append("Review cancellation reasons")
            recommendations.append("Assess if workflow should be resumed or restarted")
        
        # Performance recommendations
        execution_time = self._calculate_performance_metrics(workflow_state, history).get("execution_time", 0)
        if execution_time > 300:  # 5 minutes
            recommendations.append("Optimize node execution times")
            recommendations.append("Consider parallel execution for independent nodes")
        
        return recommendations
    
    def _calculate_system_performance_metrics(self, workflows: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate system-wide performance metrics"""
        if not workflows:
            return {"throughput": 0, "avg_execution_time": 0, "success_rate": 0}
        
        # Calculate throughput (workflows per hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_workflows = 0
        
        for workflow in workflows:
            try:
                workflow_time = datetime.fromisoformat(workflow["timestamp"])
                if workflow_time >= cutoff_time:
                    recent_workflows += 1
            except Exception:
                continue
        
        throughput = recent_workflows / 1.0  # per hour
        
        # Calculate success rate
        completed_workflows = len([w for w in workflows if w["status"] == "completed"])
        total_workflows = len(workflows)
        success_rate = completed_workflows / total_workflows if total_workflows > 0 else 0
        
        return {
            "throughput": throughput,
            "avg_execution_time": 120,  # Placeholder - would calculate actual times
            "success_rate": success_rate
        }
    
    def _calculate_resource_utilization(self) -> Dict[str, float]:
        """Calculate resource utilization metrics"""
        # These would typically come from system monitoring
        return {
            "cpu_usage": 0.45,    # 45% CPU usage
            "memory_usage": 0.62, # 62% memory usage
            "redis_memory": 0.34, # 34% Redis memory usage
            "network_io": 0.12    # 12% network I/O
        }
    
    def _get_recent_alerts(self, workflows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get recent alerts from workflow data"""
        return self._check_alert_conditions(workflows)
    
    def _generate_system_recommendations(self, system_metrics: Dict[str, Any], performance: Dict[str, float]) -> List[str]:
        """Generate system-wide recommendations"""
        recommendations = []
        
        # Performance recommendations
        if performance.get("success_rate", 0) < 0.9:
            recommendations.append("Investigate workflow failure patterns")
            recommendations.append("Improve error handling and recovery mechanisms")
        
        if performance.get("throughput", 0) < 10:
            recommendations.append("Consider scaling workflow execution capacity")
            recommendations.append("Optimize node execution performance")
        
        # Resource recommendations
        # These would come from actual monitoring data
        recommendations.append("Monitor Redis memory usage and implement cleanup")
        recommendations.append("Consider implementing workflow priority queuing")
        
        return recommendations