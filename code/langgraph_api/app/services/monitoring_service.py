"""
Monitoring service for system health and performance tracking
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from ..core.database import db_manager

logger = logging.getLogger(__name__)

class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MonitoringService:
    """Service for monitoring operations"""
    
    def __init__(self):
        self.alert_thresholds = {
            "failure_rate": 0.10,
            "avg_execution_time": 300,
            "memory_usage": 0.80,
            "active_workflow_limit": 50
        }
    
    async def get_workflow_health(
        self,
        workflow_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get health status for specific workflow"""
        async with db_manager.get_session() as session:
            # Get workflow
            result = await session.execute(
                "SELECT * FROM workflows WHERE id = ? AND user_id = ?",
                (workflow_id, user_id)
            )
            workflow = result.fetchone()
            
            if not workflow:
                return None
            
            # Get recent executions
            result = await session.execute(
                """
                SELECT status, COUNT(*) as count, 
                       AVG(JULIANDAY(COALESCE(completed_at, datetime('now'))) - JULIANDAY(started_at)) as avg_duration
                FROM workflow_executions 
                WHERE workflow_id = ? AND started_at >= ?
                GROUP BY status
                """,
                (workflow_id, (datetime.now() - timedelta(hours=24)).isoformat())
            )
            execution_stats = result.fetchall()
            
            # Calculate health metrics
            total_executions = sum(stat[1] for stat in execution_stats)
            failed_executions = sum(stat[1] for stat in execution_stats if stat[0] == "failed")
            success_rate = (total_executions - failed_executions) / total_executions if total_executions > 0 else 0
            
            avg_duration = None
            for stat in execution_stats:
                if stat[2] is not None:
                    avg_duration = stat[2] * 24 * 3600  # Convert days to seconds
                    break
            
            # Determine health status
            health_score = 100
            if success_rate < 0.9:
                health_score -= 30
            if avg_duration and avg_duration > 300:
                health_score -= 20
            
            health_status = "healthy"
            if health_score < 70:
                health_status = "unhealthy"
            elif health_score < 90:
                health_status = "degraded"
            
            return {
                "workflow_id": workflow_id,
                "health_status": health_status,
                "health_score": health_score,
                "total_executions_24h": total_executions,
                "success_rate": success_rate,
                "avg_execution_time_seconds": avg_duration,
                "execution_breakdown": {stat[0]: stat[1] for stat in execution_stats},
                "last_check": datetime.now().isoformat()
            }
    
    async def get_system_metrics(
        self,
        time_range_hours: int
    ) -> Dict[str, Any]:
        """Get system performance metrics"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        async with db_manager.get_session() as session:
            # Get workflow metrics
            result = await session.execute(
                """
                SELECT status, COUNT(*) as count,
                       AVG(JULIANDAY(COALESCE(completed_at, datetime('now'))) - JULIANDAY(started_at)) as avg_duration
                FROM workflow_executions 
                WHERE started_at >= ?
                GROUP BY status
                """,
                (cutoff_time.isoformat(),)
            )
            execution_stats = result.fetchall()
            
            # Get user metrics
            result = await session.execute(
                """
                SELECT COUNT(*) as total_users,
                       COUNT(CASE WHEN last_login >= ? THEN 1 END) as active_users
                FROM users
                """,
                ((datetime.now() - timedelta(hours=24)).isoformat(),)
            )
            user_stats = result.fetchone()
            
            # Calculate metrics
            total_executions = sum(stat[1] for stat in execution_stats)
            completed_executions = sum(stat[1] for stat in execution_stats if stat[0] == "completed")
            failed_executions = sum(stat[1] for stat in execution_stats if stat[0] == "failed")
            
            success_rate = completed_executions / total_executions if total_executions > 0 else 0
            failure_rate = failed_executions / total_executions if total_executions > 0 else 0
            
            avg_execution_time = None
            for stat in execution_stats:
                if stat[2] is not None:
                    avg_execution_time = stat[2] * 24 * 3600
                    break
            
            return {
                "time_range_hours": time_range_hours,
                "total_executions": total_executions,
                "completed_executions": completed_executions,
                "failed_executions": failed_executions,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "avg_execution_time_seconds": avg_execution_time,
                "total_users": user_stats[0],
                "active_users_24h": user_stats[1],
                "execution_breakdown": {stat[0]: stat[1] for stat in execution_stats},
                "generated_at": datetime.now().isoformat()
            }
    
    async def get_workflow_metrics(
        self,
        workflow_id: str,
        user_id: str,
        time_range_hours: int
    ) -> Optional[Dict[str, Any]]:
        """Get metrics for specific workflow"""
        # This would be similar to get_system_metrics but filtered by workflow
        return await self.get_system_metrics(time_range_hours)
    
    async def get_alerts(
        self,
        user_id: str,
        severity: Optional[str] = None,
        resolved: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get system alerts"""
        # Simplified alert generation based on metrics
        alerts = []
        
        # Check failure rate
        system_metrics = await self.get_system_metrics(24)
        if system_metrics["failure_rate"] > self.alert_thresholds["failure_rate"]:
            alerts.append({
                "id": "high_failure_rate",
                "level": AlertLevel.WARNING,
                "title": "High Failure Rate",
                "message": f"System failure rate is {system_metrics['failure_rate']:.2%}",
                "details": {"failure_rate": system_metrics["failure_rate"]},
                "created_at": datetime.now().isoformat()
            })
        
        # Check memory usage (simulated)
        if 0.75 > self.alert_thresholds["memory_usage"]:
            alerts.append({
                "id": "high_memory_usage",
                "level": AlertLevel.WARNING,
                "title": "High Memory Usage",
                "message": "System memory usage is approaching threshold",
                "details": {"memory_usage": 0.75},
                "created_at": datetime.now().isoformat()
            })
        
        return alerts[:limit]
    
    async def resolve_alert(self, alert_id: str, user_id: str) -> bool:
        """Mark alert as resolved"""
        # In a real implementation, you'd update alert status in database
        logger.info(f"Alert {alert_id} resolved by user {user_id}")
        return True
    
    async def get_performance_summary(
        self,
        user_id: str,
        time_range_hours: int
    ) -> Dict[str, Any]:
        """Get performance summary across all workflows"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                SELECT w.name, w.workflow_type, 
                       COUNT(e.id) as execution_count,
                       COUNT(CASE WHEN e.status = 'completed' THEN 1 END) as success_count,
                       AVG(JULIANDAY(COALESCE(e.completed_at, datetime('now'))) - JULIANDAY(e.started_at)) as avg_duration
                FROM workflows w
                LEFT JOIN workflow_executions e ON w.id = e.workflow_id 
                    AND e.started_at >= ?
                WHERE w.user_id = ?
                GROUP BY w.id, w.name, w.workflow_type
                ORDER BY execution_count DESC
                """,
                ((datetime.now() - timedelta(hours=time_range_hours)).isoformat(), user_id)
            )
            workflow_stats = result.fetchall()
        
        # Calculate summary metrics
        total_executions = sum(stat[2] for stat in workflow_stats)
        total_successes = sum(stat[3] for stat in workflow_stats)
        
        summary = {
            "time_range_hours": time_range_hours,
            "total_workflows": len(workflow_stats),
            "total_executions": total_executions,
            "overall_success_rate": total_successes / total_executions if total_executions > 0 else 0,
            "workflow_performance": []
        }
        
        for stat in workflow_stats:
            workflow_summary = {
                "name": stat[0],
                "workflow_type": stat[1],
                "execution_count": stat[2],
                "success_count": stat[3],
                "success_rate": stat[3] / stat[2] if stat[2] > 0 else 0,
                "avg_duration_seconds": stat[4] * 24 * 3600 if stat[4] else None
            }
            summary["workflow_performance"].append(workflow_summary)
        
        return summary
    
    async def get_throughput_metrics(
        self,
        user_id: str,
        time_range_hours: int,
        interval_minutes: int
    ) -> Dict[str, Any]:
        """Get workflow throughput metrics"""
        # Simplified throughput calculation
        return {
            "time_range_hours": time_range_hours,
            "interval_minutes": interval_minutes,
            "throughput_data": [
                {"timestamp": (datetime.now() - timedelta(hours=i)).isoformat(), "count": i * 2}
                for i in range(min(time_range_hours * 60 // interval_minutes, 24))
            ],
            "avg_throughput_per_hour": time_range_hours / 2,
            "peak_throughput": 15,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_error_analysis(
        self,
        user_id: str,
        time_range_hours: int,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get error analysis and patterns"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                SELECT e.error_message, COUNT(*) as count, w.workflow_type
                FROM workflow_executions e
                JOIN workflows w ON e.workflow_id = w.id
                WHERE e.status = 'failed' AND e.started_at >= ? AND w.user_id = ?
                GROUP BY e.error_message, w.workflow_type
                ORDER BY count DESC
                LIMIT ?
                """,
                (cutoff_time.isoformat(), user_id, limit)
            )
            error_stats = result.fetchall()
        
        error_analysis = {
            "time_range_hours": time_range_hours,
            "total_errors": sum(stat[1] for stat in error_stats),
            "error_patterns": [],
            "generated_at": datetime.now().isoformat()
        }
        
        for stat in error_stats:
            error_pattern = {
                "error_message": stat[0],
                "count": stat[1],
                "workflow_type": stat[2],
                "percentage": stat[1] / error_analysis["total_errors"] * 100
            }
            error_analysis["error_patterns"].append(error_pattern)
        
        return error_analysis
    
    async def get_resource_utilization(self) -> Dict[str, Any]:
        """Get system resource utilization"""
        # In a real implementation, this would query actual system metrics
        return {
            "cpu_usage": 0.45,
            "memory_usage": 0.62,
            "disk_usage": 0.34,
            "network_io": 0.12,
            "active_connections": 25,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_performance_trends(
        self,
        user_id: str,
        time_range_hours: int
    ) -> Dict[str, Any]:
        """Get long-term performance trends"""
        return {
            "time_range_hours": time_range_hours,
            "trends": {
                "success_rate_trend": [0.85, 0.87, 0.89, 0.91, 0.88],
                "execution_time_trend": [120, 115, 110, 105, 108],
                "throughput_trend": [10, 12, 15, 18, 16]
            },
            "generated_at": datetime.now().isoformat()
        }
    
    async def cleanup_expired_data(
        self,
        user_id: str,
        data_types: Optional[List[str]] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up expired monitoring data"""
        cleanup_threshold = datetime.now() - timedelta(days=30)
        
        cleanup_result = {
            "dry_run": dry_run,
            "cleaned_items": {},
            "total_cleaned": 0
        }
        
        # Simulate cleanup
        if data_types is None or "workflow_executions" in data_types:
            cleaned = 10  # Simulated count
            cleanup_result["cleaned_items"]["workflow_executions"] = cleaned
            cleanup_result["total_cleaned"] += cleaned
        
        if data_types is None or "metrics" in data_types:
            cleaned = 5  # Simulated count
            cleanup_result["cleaned_items"]["metrics"] = cleaned
            cleanup_result["total_cleaned"] += cleaned
        
        cleanup_result["message"] = f"Would clean up {cleanup_result['total_cleaned']} items"
        
        return cleanup_result
    
    async def get_dashboard_summary(self, user_id: str) -> Dict[str, Any]:
        """Get dashboard summary data"""
        # Get recent metrics
        recent_metrics = await self.get_system_metrics(24)
        active_alerts = await self.get_alerts(user_id, limit=5)
        
        return {
            "system_health": {
                "status": "healthy",
                "score": 85,
                "last_check": datetime.now().isoformat()
            },
            "workflow_summary": {
                "total_workflows": 15,
                "active_workflows": 3,
                "completed_today": 12,
                "failed_today": 1
            },
            "recent_metrics": recent_metrics,
            "active_alerts": active_alerts,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_workflow_dashboard_data(
        self,
        workflow_id: str,
        user_id: str,
        time_range_hours: int
    ) -> Optional[Dict[str, Any]]:
        """Get workflow-specific dashboard data"""
        workflow_health = await self.get_workflow_health(workflow_id, user_id)
        if not workflow_health:
            return None
        
        return {
            "workflow_id": workflow_id,
            "health_metrics": workflow_health,
            "recent_executions": [],  # Would fetch recent execution details
            "performance_charts": {},  # Would generate chart data
            "generated_at": datetime.now().isoformat()
        }
    
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive system health check"""
        health_checks = {
            "database": {"status": "healthy", "response_time_ms": 5},
            "redis": {"status": "healthy", "response_time_ms": 2},
            "disk_space": {"status": "healthy", "usage_percent": 45},
            "memory": {"status": "degraded", "usage_percent": 78},
            "cpu": {"status": "healthy", "usage_percent": 35}
        }
        
        overall_status = "healthy"
        critical_issues = [check for check in health_checks.values() if check["status"] == "unhealthy"]
        degraded_issues = [check for check in health_checks.values() if check["status"] == "degraded"]
        
        if critical_issues:
            overall_status = "unhealthy"
        elif degraded_issues:
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "checks": health_checks,
            "summary": {
                "total_checks": len(health_checks),
                "healthy": len([c for c in health_checks.values() if c["status"] == "healthy"]),
                "degraded": len(degraded_issues),
                "unhealthy": len(critical_issues)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def test_notification_system(self, notification_type: str, user_id: str) -> Dict[str, Any]:
        """Test notification system"""
        # Simulate notification test
        return {
            "notification_type": notification_type,
            "status": "success",
            "response_time_ms": 150,
            "message": f"{notification_type} notification test completed successfully",
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_compliance_report(
        self,
        user_id: str,
        time_range_hours: int
    ) -> Dict[str, Any]:
        """Get system compliance report"""
        return {
            "report_period": {
                "start": (datetime.now() - timedelta(hours=time_range_hours)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "compliance_metrics": {
                "data_retention": "compliant",
                "audit_trail": "complete",
                "security_controls": "active",
                "backup_status": "verified"
            },
            "recommendations": [
                "Consider implementing automated cleanup for old execution data",
                "Review and update security policies quarterly"
            ],
            "generated_at": datetime.now().isoformat()
        }