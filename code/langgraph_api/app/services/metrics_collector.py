"""
Metrics collector for Prometheus-compatible metrics
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from ..core.database import db_manager

logger = logging.getLogger(__name__)

# Prometheus metrics
workflow_executions_total = Counter('workflow_executions_total', 'Total workflow executions', ['status'])
workflow_execution_duration = Histogram('workflow_execution_duration_seconds', 'Workflow execution duration')
active_workflows = Gauge('active_workflows', 'Number of active workflows')
system_health_score = Gauge('system_health_score', 'System health score')
api_requests_total = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status_code'])

class MetricsCollector:
    """Metrics collection service"""
    
    def __init__(self):
        self.collecting_active = False
        self.collection_interval = 60  # seconds
        self.metrics_buffer = []
        
    def start(self):
        """Start metrics collection"""
        self.collecting_active = True
        logger.info("Metrics collector started")
        
        # Start background collection task
        import asyncio
        asyncio.create_task(self._collection_loop())
    
    def stop(self):
        """Stop metrics collection"""
        self.collecting_active = False
        logger.info("Metrics collector stopped")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        try:
            # Get Prometheus metrics
            prometheus_metrics = generate_latest().decode('utf-8')
            
            # Get custom metrics
            custom_metrics = await self._collect_custom_metrics()
            
            return {
                "prometheus_metrics": prometheus_metrics,
                "custom_metrics": custom_metrics,
                "timestamp": datetime.now().isoformat(),
                "content_type": CONTENT_TYPE_LATEST
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_custom_metrics(self) -> Dict[str, Any]:
        """Collect custom application metrics"""
        try:
            async with db_manager.get_session() as session:
                # Workflow metrics
                result = await session.execute("""
                    SELECT status, COUNT(*) 
                    FROM workflows 
                    GROUP BY status
                """)
                workflow_stats = dict(result.fetchall())
                
                # Recent execution metrics
                result = await session.execute("""
                    SELECT status, COUNT(*), 
                           AVG(JULIANDAY(COALESCE(completed_at, datetime('now'))) - JULIANDAY(started_at))
                    FROM workflow_executions 
                    WHERE started_at >= ?
                    GROUP BY status
                """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
                execution_stats = result.fetchall()
                
                # User metrics
                result = await session.execute("""
                    SELECT COUNT(*) as total_users,
                           COUNT(CASE WHEN last_login >= ? THEN 1 END) as active_users
                    FROM users
                """, ((datetime.now() - timedelta(hours=24)).isoformat(),))
                user_stats = result.fetchone()
            
            # Calculate derived metrics
            total_workflows = sum(workflow_stats.values())
            active_workflows_count = workflow_stats.get("running", 0)
            completed_24h = sum(stat[1] for stat in execution_stats if stat[0] == "completed")
            failed_24h = sum(stat[1] for stat in execution_stats if stat[0] == "failed")
            
            success_rate = completed_24h / (completed_24h + failed_24h) if (completed_24h + failed_24h) > 0 else 0
            
            avg_execution_time = None
            for stat in execution_stats:
                if stat[2] is not None:
                    avg_execution_time = stat[2] * 24 * 3600  # Convert days to seconds
                    break
            
            custom_metrics = {
                "workflow_metrics": {
                    "total_workflows": total_workflows,
                    "active_workflows": active_workflows_count,
                    "workflow_by_status": workflow_stats
                },
                "execution_metrics": {
                    "executions_24h": sum(stat[1] for stat in execution_stats),
                    "success_rate_24h": success_rate,
                    "avg_execution_time_seconds": avg_execution_time
                },
                "user_metrics": {
                    "total_users": user_stats[0],
                    "active_users_24h": user_stats[1]
                },
                "system_metrics": {
                    "timestamp": datetime.now().isoformat(),
                    "collection_status": "active" if self.collecting_active else "inactive"
                }
            }
            
            # Update Prometheus gauges
            active_workflows.set(active_workflows_count)
            system_health_score.set(85)  # Would calculate actual health score
            
            return custom_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect custom metrics: {e}")
            return {"error": str(e)}
    
    async def _collection_loop(self):
        """Background metrics collection loop"""
        while self.collecting_active:
            try:
                # Collect metrics
                metrics = await self._collect_custom_metrics()
                self.metrics_buffer.append({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics
                })
                
                # Keep only last 1000 metric snapshots
                if len(self.metrics_buffer) > 1000:
                    self.metrics_buffer = self.metrics_buffer[-1000:]
                
                logger.debug("Metrics collection completed")
                
                # Sleep for collection interval
                import asyncio
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                import asyncio
                await asyncio.sleep(self.collection_interval)
    
    def record_workflow_execution(self, status: str, duration: float):
        """Record workflow execution metrics"""
        workflow_executions_total.labels(status=status).inc()
        workflow_execution_duration.observe(duration)
    
    def record_api_request(self, method: str, endpoint: str, status_code: int):
        """Record API request metrics"""
        api_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    
    async def get_historical_metrics(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get historical metrics data"""
        try:
            # Filter metrics buffer for time range and metric
            filtered_metrics = [
                m for m in self.metrics_buffer
                if start_time <= datetime.fromisoformat(m["timestamp"]) <= end_time
            ]
            
            # Aggregate by interval
            aggregated_data = []
            current_time = start_time
            
            while current_time < end_time:
                interval_end = current_time + timedelta(minutes=interval_minutes)
                
                # Get metrics for this interval
                interval_metrics = [
                    m for m in filtered_metrics
                    if current_time <= datetime.fromisoformat(m["timestamp"]) < interval_end
                ]
                
                if interval_metrics:
                    # Calculate average for the interval
                    avg_metrics = self._calculate_interval_average(interval_metrics, metric_name)
                    aggregated_data.append({
                        "timestamp": current_time.isoformat(),
                        "value": avg_metrics
                    })
                
                current_time = interval_end
            
            return {
                "metric_name": metric_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "interval_minutes": interval_minutes,
                "data_points": len(aggregated_data),
                "data": aggregated_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_interval_average(self, metrics_list: list, metric_name: str) -> float:
        """Calculate average value for a metric in the interval"""
        values = []
        
        for metric_snapshot in metrics_list:
            metrics = metric_snapshot.get("metrics", {})
            
            # Navigate to the specific metric
            value = None
            if metric_name == "active_workflows":
                value = metrics.get("workflow_metrics", {}).get("active_workflows")
            elif metric_name == "success_rate":
                value = metrics.get("execution_metrics", {}).get("success_rate_24h")
            elif metric_name == "total_executions":
                value = metrics.get("execution_metrics", {}).get("executions_24h")
            
            if value is not None:
                values.append(value)
        
        return sum(values) / len(values) if values else 0
    
    async def export_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export metrics data"""
        try:
            # Get filtered metrics
            filtered_metrics = [
                m for m in self.metrics_buffer
                if start_time <= datetime.fromisoformat(m["timestamp"]) <= end_time
            ]
            
            export_data = {
                "export_info": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "format": format,
                    "total_points": len(filtered_metrics),
                    "exported_at": datetime.now().isoformat()
                },
                "metrics": filtered_metrics
            }
            
            if format == "prometheus":
                # Export in Prometheus text format
                prometheus_text = generate_latest().decode('utf-8')
                export_data["prometheus_format"] = prometheus_text
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return {"error": str(e)}
    
    async def reset_metrics(self):
        """Reset all metrics"""
        try:
            # Reset Prometheus metrics
            from prometheus_client import REGISTRY
            for collector in list(REGISTRY._collector_to_names.keys()):
                try:
                    REGISTRY.unregister(collector)
                except:
                    pass
            
            # Reinitialize metrics
            global workflow_executions_total, workflow_execution_duration, active_workflows, system_health_score, api_requests_total
            workflow_executions_total = Counter('workflow_executions_total', 'Total workflow executions', ['status'])
            workflow_execution_duration = Histogram('workflow_execution_duration_seconds', 'Workflow execution duration')
            active_workflows = Gauge('active_workflows', 'Number of active workflows')
            system_health_score = Gauge('system_health_score', 'System health score')
            api_requests_total = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status_code'])
            
            # Clear metrics buffer
            self.metrics_buffer.clear()
            
            logger.info("Metrics reset completed")
            return {"status": "success", "message": "Metrics reset successfully"}
            
        except Exception as e:
            logger.error(f"Failed to reset metrics: {e}")
            return {"error": str(e)}