"""
Health monitoring system for Composio MCP Server.
"""

import asyncio
import json
import os
import psutil
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import structlog
from prometheus_client import Gauge, Counter, Histogram

logger = structlog.get_logger()


class HealthMonitor:
    """Health monitoring system for the MCP server."""
    
    def __init__(self, settings):
        """Initialize health monitor."""
        self.settings = settings
        self.start_time = time.time()
        self.is_monitoring = False
        
        # Health check intervals
        self.check_interval = settings.health.check_interval
        self.timeout = settings.health.timeout
        
        # Alert thresholds
        self.alert_thresholds = settings.health.alert_thresholds
        
        # Prometheus metrics
        self.cpu_usage_gauge = Gauge('composio_cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage_gauge = Gauge('composio_memory_usage_percent', 'Memory usage percentage')
        self.disk_usage_gauge = Gauge('composio_disk_usage_percent', 'Disk usage percentage')
        self.response_time_gauge = Gauge('composio_response_time_ms', 'Average response time in milliseconds')
        self.active_connections_gauge = Gauge('composio_active_connections', 'Number of active connections')
        
        # Health check results cache
        self.last_health_check = None
        self.health_history = []
        
        # External service health status
        self.external_services_health = {}
        
        logger.info("Health monitor initialized", check_interval=self.check_interval)
    
    async def start(self):
        """Start health monitoring."""
        if not self.settings.health.enabled:
            logger.info("Health monitoring disabled")
            return
        
        self.is_monitoring = True
        
        # Start health check tasks
        tasks = [
            asyncio.create_task(self._monitor_system_resources()),
            asyncio.create_task(self._monitor_external_services()),
            asyncio.create_task(self._cleanup_history()),
        ]
        
        logger.info("Health monitoring started")
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error("Health monitoring error", error=str(e))
    
    async def stop(self):
        """Stop health monitoring."""
        self.is_monitoring = False
        logger.info("Health monitoring stopped")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        try:
            # Get system resource status
            system_status = await self._get_system_status()
            
            # Get external services status
            services_status = self.external_services_health.copy()
            
            # Get application status
            app_status = await self._get_application_status()
            
            # Calculate overall health
            overall_health = self._calculate_overall_health(system_status, services_status, app_status)
            
            # Get uptime
            uptime_seconds = time.time() - self.start_time
            
            health_status = {
                "overall": overall_health,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": uptime_seconds,
                "uptime_hours": round(uptime_seconds / 3600, 2),
                "system": system_status,
                "services": services_status,
                "application": app_status,
                "version": "1.0.0"
            }
            
            # Cache the result
            self.last_health_check = health_status
            
            return health_status
            
        except Exception as e:
            logger.error("Failed to get health status", error=str(e))
            return {
                "overall": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def _monitor_system_resources(self):
        """Monitor system resources continuously."""
        while self.is_monitoring:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Update Prometheus metrics
                self.cpu_usage_gauge.set(cpu_percent)
                self.memory_usage_gauge.set(memory.percent)
                self.disk_usage_gauge.set((disk.used / disk.total) * 100)
                
                # Check for alerts
                await self._check_system_alerts(cpu_percent, memory.percent, (disk.used / disk.total) * 100)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error("System resource monitoring error", error=str(e))
                await asyncio.sleep(self.check_interval)
    
    async def _monitor_external_services(self):
        """Monitor external service health."""
        services_to_check = [
            ("redis", self._check_redis_health),
            ("database", self._check_database_health),
        ]
        
        while self.is_monitoring:
            try:
                health_results = {}
                
                for service_name, check_function in services_to_check:
                    try:
                        is_healthy = await check_function()
                        health_results[service_name] = {
                            "status": "healthy" if is_healthy else "unhealthy",
                            "last_check": datetime.utcnow().isoformat()
                        }
                    except Exception as e:
                        logger.warning(f"Health check failed for {service_name}", error=str(e))
                        health_results[service_name] = {
                            "status": "unhealthy",
                            "error": str(e),
                            "last_check": datetime.utcnow().isoformat()
                        }
                
                self.external_services_health = health_results
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error("External services monitoring error", error=str(e))
                await asyncio.sleep(self.check_interval)
    
    async def _check_redis_health(self) -> bool:
        """Check Redis health."""
        try:
            # Test Redis connection if available
            # This would typically use the Redis client from settings
            return True  # Placeholder
        except Exception:
            return False
    
    async def _check_database_health(self) -> bool:
        """Check database health."""
        try:
            # Test database connection
            # This would typically test the database connection
            return True  # Placeholder
        except Exception:
            return False
    
    async def _check_system_alerts(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Check system metrics against alert thresholds."""
        if cpu_percent > self.alert_thresholds.get("cpu_usage", 80):
            logger.warning("High CPU usage detected", cpu_percent=cpu_percent)
        
        if memory_percent > self.alert_thresholds.get("memory_usage", 85):
            logger.warning("High memory usage detected", memory_percent=memory_percent)
        
        if disk_percent > self.alert_thresholds.get("disk_usage", 90):
            logger.warning("High disk usage detected", disk_percent=disk_percent)
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "load_average": load_avg,
                    "cores": psutil.cpu_count(),
                    "status": "healthy" if cpu_percent < self.alert_thresholds.get("cpu_usage", 80) else "warning"
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "status": "healthy" if memory.percent < self.alert_thresholds.get("memory_usage", 85) else "warning"
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2),
                    "status": "healthy" if (disk.used / disk.total) * 100 < self.alert_thresholds.get("disk_usage", 90) else "warning"
                },
                "processes": {
                    "total": len(psutil.pids()),
                    "status": "running"
                }
            }
            
        except Exception as e:
            logger.error("Failed to get system status", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def _get_application_status(self) -> Dict[str, Any]:
        """Get application-specific status."""
        try:
            uptime_seconds = time.time() - self.start_time
            
            return {
                "status": "running",
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": str(timedelta(seconds=int(uptime_seconds))),
                "version": "1.0.0",
                "environment": self.settings.environment,
                "features": list(self.settings.features.keys()),
                "tools_loaded": len(getattr(self, 'tool_handlers', {})),
                "last_restart": datetime.fromtimestamp(self.start_time).isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get application status", error=str(e))
            return {"status": "error", "error": str(e)}
    
    def _calculate_overall_health(self, system_status: Dict, services_status: Dict, app_status: Dict) -> str:
        """Calculate overall health status."""
        unhealthy_components = []
        
        # Check system health
        if system_status.get("cpu", {}).get("status") == "warning":
            unhealthy_components.append("cpu")
        if system_status.get("memory", {}).get("status") == "warning":
            unhealthy_components.append("memory")
        if system_status.get("disk", {}).get("status") == "warning":
            unhealthy_components.append("disk")
        
        # Check services health
        for service, status in services_status.items():
            if status.get("status") != "healthy":
                unhealthy_components.append(service)
        
        # Check application health
        if app_status.get("status") != "running":
            unhealthy_components.append("application")
        
        # Determine overall health
        if not unhealthy_components:
            return "healthy"
        elif len(unhealthy_components) <= 2:
            return "degraded"
        else:
            return "unhealthy"
    
    async def _cleanup_history(self):
        """Clean up old health history entries."""
        while self.is_monitoring:
            try:
                current_time = datetime.utcnow()
                cutoff_time = current_time - timedelta(hours=24)  # Keep 24 hours
                
                # Remove old entries
                self.health_history = [
                    entry for entry in self.health_history
                    if datetime.fromisoformat(entry["timestamp"]) > cutoff_time
                ]
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error("Health history cleanup error", error=str(e))
                await asyncio.sleep(3600)
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat()
    
    async def get_uptime(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self.start_time
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed health metrics."""
        try:
            health_status = await self.get_health_status()
            
            # Add historical data
            metrics = {
                "current": health_status,
                "history": self.health_history[-10:],  # Last 10 entries
                "trends": await self._calculate_trends(),
                "recommendations": await self._generate_recommendations(health_status)
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get detailed metrics", error=str(e))
            return {"error": str(e)}
    
    async def _calculate_trends(self) -> Dict[str, float]:
        """Calculate health trends from history."""
        try:
            if len(self.health_history) < 2:
                return {}
            
            # Calculate CPU trend
            cpu_values = [
                entry.get("system", {}).get("cpu", {}).get("usage_percent", 0)
                for entry in self.health_history[-10:]
                if entry.get("system", {}).get("cpu", {}).get("usage_percent") is not None
            ]
            
            cpu_trend = 0
            if len(cpu_values) >= 2:
                cpu_trend = (cpu_values[-1] - cpu_values[0]) / len(cpu_values)
            
            # Calculate memory trend
            memory_values = [
                entry.get("system", {}).get("memory", {}).get("usage_percent", 0)
                for entry in self.health_history[-10:]
                if entry.get("system", {}).get("memory", {}).get("usage_percent") is not None
            ]
            
            memory_trend = 0
            if len(memory_values) >= 2:
                memory_trend = (memory_values[-1] - memory_values[0]) / len(memory_values)
            
            return {
                "cpu_trend": round(cpu_trend, 2),
                "memory_trend": round(memory_trend, 2)
            }
            
        except Exception as e:
            logger.error("Failed to calculate trends", error=str(e))
            return {}
    
    async def _generate_recommendations(self, health_status: Dict[str, Any]) -> List[str]:
        """Generate health recommendations."""
        recommendations = []
        
        try:
            # Check CPU usage
            cpu_usage = health_status.get("system", {}).get("cpu", {}).get("usage_percent", 0)
            if cpu_usage > 70:
                recommendations.append("Consider scaling up CPU resources or optimizing CPU-intensive operations")
            
            # Check memory usage
            memory_usage = health_status.get("system", {}).get("memory", {}).get("usage_percent", 0)
            if memory_usage > 80:
                recommendations.append("Monitor memory usage and consider scaling up or optimizing memory usage")
            
            # Check disk usage
            disk_usage = health_status.get("system", {}).get("disk", {}).get("usage_percent", 0)
            if disk_usage > 85:
                recommendations.append("Disk space is running low. Consider cleaning up or expanding storage")
            
            # Check for unhealthy services
            unhealthy_services = [
                service for service, status in health_status.get("services", {}).items()
                if status.get("status") != "healthy"
            ]
            
            if unhealthy_services:
                recommendations.append(f"Investigate and fix unhealthy services: {', '.join(unhealthy_services)}")
            
            # Check uptime
            uptime_hours = health_status.get("uptime_hours", 0)
            if uptime_hours < 1:
                recommendations.append("Server has recently started. Monitor initial performance metrics")
            elif uptime_hours > 720:  # 30 days
                recommendations.append("Consider scheduling a maintenance restart for optimal performance")
            
            return recommendations
            
        except Exception as e:
            logger.error("Failed to generate recommendations", error=str(e))
            return ["Unable to generate recommendations due to an error"]
    
    async def create_health_snapshot(self) -> Dict[str, Any]:
        """Create a comprehensive health snapshot."""
        try:
            current_health = await self.get_health_status()
            
            snapshot = {
                "snapshot_id": f"health_{int(time.time())}",
                "timestamp": datetime.utcnow().isoformat(),
                "server_info": {
                    "version": "1.0.0",
                    "environment": self.settings.environment,
                    "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
                },
                "health": current_health,
                "system_info": {
                    "platform": os.name,
                    "python_version": "3.x",
                    "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "cpu_cores": psutil.cpu_count(),
                    "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2)
                },
                "performance": await self._get_performance_metrics()
            }
            
            return snapshot
            
        except Exception as e:
            logger.error("Failed to create health snapshot", error=str(e))
            return {"error": str(e)}
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            return {
                "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
                "uptime_seconds": uptime_seconds,
                "network_io": dict(psutil.net_io_counters()._asdict()) if psutil.net_io_counters() else {},
                "disk_io": dict(psutil.disk_io_counters()._asdict()) if psutil.disk_io_counters() else {},
                "process_count": len(psutil.pids())
            }
            
        except Exception as e:
            logger.error("Failed to get performance metrics", error=str(e))
            return {"error": str(e)}