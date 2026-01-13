"""
Health monitor for system health tracking
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from ..core.database import db_manager

logger = logging.getLogger(__name__)

class HealthMonitor:
    """System health monitoring service"""
    
    def __init__(self):
        self.monitoring_active = False
        self.last_health_check = None
        self.health_history = []
        self.monitoring_interval = 60  # seconds
        
    def start(self):
        """Start health monitoring"""
        self.monitoring_active = True
        logger.info("Health monitor started")
        
        # Start background monitoring task
        asyncio.create_task(self._monitoring_loop())
    
    def stop(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        logger.info("Health monitor stopped")
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        health_data = {
            "overall_status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "metrics": {},
            "alerts": []
        }
        
        try:
            # Check database health
            db_health = await self._check_database_health()
            health_data["components"]["database"] = db_health
            
            # Check Redis health
            redis_health = await self._check_redis_health()
            health_data["components"]["redis"] = redis_health
            
            # Check workflow system health
            workflow_health = await self._check_workflow_health()
            health_data["components"]["workflow_system"] = workflow_health
            
            # Check system resources
            resource_health = await self._check_resource_health()
            health_data["components"]["system_resources"] = resource_health
            
            # Calculate overall health score
            health_score = self._calculate_health_score(health_data["components"])
            health_data["health_score"] = health_score
            
            # Determine overall status
            if health_score >= 90:
                health_data["overall_status"] = "healthy"
            elif health_score >= 70:
                health_data["overall_status"] = "degraded"
            else:
                health_data["overall_status"] = "unhealthy"
            
            # Add metrics
            health_data["metrics"] = await self._collect_health_metrics()
            
            # Add alerts if any
            health_data["alerts"] = self._generate_health_alerts(health_data["components"])
            
            self.last_health_check = datetime.now()
            self.health_history.append(health_data)
            
            # Keep only last 100 health checks
            if len(self.health_history) > 100:
                self.health_history = self.health_history[-100:]
            
            return health_data
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_data["overall_status"] = "unhealthy"
            health_data["error"] = str(e)
            return health_data
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            start_time = datetime.now()
            
            async with db_manager.get_session() as session:
                # Test basic query
                await session.execute("SELECT 1")
                
                # Test workflow table access
                result = await session.execute("SELECT COUNT(*) FROM workflows")
                workflow_count = result.fetchone()[0]
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy" if response_time < 100 else "degraded",
                "response_time_ms": response_time,
                "workflow_count": workflow_count
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            start_time = datetime.now()
            
            redis_client = await db_manager.get_redis()
            await redis_client.ping()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                "status": "healthy" if response_time < 50 else "degraded",
                "response_time_ms": response_time
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_workflow_health(self) -> Dict[str, Any]:
        """Check workflow system health"""
        try:
            async with db_manager.get_session() as session:
                # Count workflows by status
                result = await session.execute("""
                    SELECT status, COUNT(*) 
                    FROM workflows 
                    GROUP BY status
                """)
                status_counts = dict(result.fetchall())
                
                # Check for stuck workflows
                result = await session.execute("""
                    SELECT COUNT(*) 
                    FROM workflows 
                    WHERE status = 'running' 
                    AND updated_at < ?
                """, ((datetime.now() - timedelta(hours=1)).isoformat(),))
                stuck_workflows = result.fetchone()[0]
            
            total_workflows = sum(status_counts.values())
            active_workflows = status_counts.get("running", 0)
            failed_workflows = status_counts.get("failed", 0)
            
            # Determine status
            if stuck_workflows > 0:
                status = "degraded"
            elif total_workflows == 0:
                status = "healthy"
            elif failed_workflows / total_workflows > 0.1:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "total_workflows": total_workflows,
                "active_workflows": active_workflows,
                "failed_workflows": failed_workflows,
                "stuck_workflows": stuck_workflows,
                "success_rate": (total_workflows - failed_workflows) / total_workflows if total_workflows > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Workflow health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def _check_resource_health(self) -> Dict[str, Any]:
        """Check system resource health"""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = "unhealthy"
            elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 70:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "load_average": getattr(psutil, 'getloadavg', lambda: [0, 0, 0])()[0] if hasattr(psutil, 'getloadavg') else 0
            }
            
        except Exception as e:
            logger.error(f"Resource health check failed: {e}")
            return {
                "status": "unknown",
                "error": str(e)
            }
    
    def _calculate_health_score(self, components: Dict[str, Dict[str, Any]]) -> int:
        """Calculate overall health score"""
        total_score = 0
        component_count = 0
        
        for component, health in components.items():
            if component == "system_resources":
                # Resources get weight of 3
                if health.get("status") == "healthy":
                    total_score += 30
                elif health.get("status") == "degraded":
                    total_score += 20
                else:
                    total_score += 0
                component_count += 3
            else:
                # Other components get weight of 1
                if health.get("status") == "healthy":
                    total_score += 10
                elif health.get("status") == "degraded":
                    total_score += 5
                else:
                    total_score += 0
                component_count += 1
        
        return min(100, total_score)
    
    async def _collect_health_metrics(self) -> Dict[str, Any]:
        """Collect health metrics"""
        try:
            async with db_manager.get_session() as session:
                # Get current metrics
                result = await session.execute("""
                    SELECT 
                        COUNT(*) as total_workflows,
                        COUNT(CASE WHEN status = 'running' THEN 1 END) as active_workflows,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_workflows,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_workflows
                    FROM workflows
                """)
                workflow_metrics = dict(result.fetchall())
                
                # Get execution metrics
                result = await session.execute("""
                    SELECT COUNT(*) as total_executions
                    FROM workflow_executions
                    WHERE started_at >= ?
                """, ((datetime.now() - timedelta(hours=1)).isoformat(),))
                recent_executions = result.fetchone()[0]
            
            return {
                "workflows": workflow_metrics,
                "recent_executions_1h": recent_executions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to collect health metrics: {e}")
            return {"error": str(e)}
    
    def _generate_health_alerts(self, components: Dict[str, Dict[str, Any]]) -> list:
        """Generate health alerts"""
        alerts = []
        
        for component, health in components.items():
            if health.get("status") == "unhealthy":
                alerts.append({
                    "component": component,
                    "level": "critical",
                    "message": f"{component} is unhealthy",
                    "details": health
                })
            elif health.get("status") == "degraded":
                alerts.append({
                    "component": component,
                    "level": "warning",
                    "message": f"{component} is degraded",
                    "details": health
                })
        
        return alerts
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                health_data = await self.get_comprehensive_health()
                logger.debug(f"Health check completed: {health_data['overall_status']}")
                
                # Sleep for monitoring interval
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def get_component_health(self, component: str) -> Optional[Dict[str, Any]]:
        """Get health status of specific component"""
        health_data = await self.get_comprehensive_health()
        return health_data.get("components", {}).get(component)
    
    async def get_health_history(self, hours: int = 24) -> list:
        """Get health check history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            check for check in self.health_history
            if datetime.fromisoformat(check["timestamp"]) >= cutoff_time
        ]
    
    async def trigger_health_check(self) -> Dict[str, Any]:
        """Manually trigger health check"""
        return await self.get_comprehensive_health()