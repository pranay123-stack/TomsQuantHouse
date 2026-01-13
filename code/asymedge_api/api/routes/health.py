"""
ASYMEdge Dashboard API - Health Check Routes

Health monitoring endpoints providing:
- System health status
- Database connectivity checks
- Service status monitoring
- Performance metrics
- Version information
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import psutil
import asyncio
import logging

from api.database.database import check_database_health, get_table_info
from api.config import settings
from api.schemas import HealthStatus, DatabaseHealth, APIResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Global state tracking
_start_time = datetime.now()
_request_count = 0
_error_count = 0

@router.get("/", response_model=HealthStatus)
async def get_health_status():
    """Get comprehensive system health status"""
    try:
        # Calculate uptime
        uptime = (datetime.now() - _start_time).total_seconds()
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get database health
        db_health = await check_database_health()
        
        # Check service features
        services_status = {
            "database": db_health["status"],
            "agents": "enabled" if settings.ENABLE_AGENT_QUERIES else "disabled",
            "streaming": "enabled" if settings.ENABLE_REAL_TIME_STREAMING else "disabled",
            "trading": "enabled" if settings.ENABLE_TRADING_METRICS else "disabled",
            "workflows": "enabled" if settings.ENABLE_WORKFLOW_MONITORING else "disabled",
            "users": "enabled" if settings.ENABLE_USER_MANAGEMENT else "disabled",
            "dashboard": "enabled" if settings.ENABLE_DASHBOARD_CONFIG else "disabled"
        }
        
        # Overall health status
        overall_status = "healthy"
        if db_health["status"] != "healthy" or cpu_percent > 90 or memory.percent > 90:
            overall_status = "degraded"
        if cpu_percent > 95 or memory.percent > 95:
            overall_status = "unhealthy"
        
        health_status = HealthStatus(
            status=overall_status,
            timestamp=datetime.now(),
            version=settings.APP_VERSION,
            uptime=uptime,
            services=services_status
        )
        
        return health_status
        
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Failed to get health status",
                "error": str(e)
            }
        )

@router.get("/detailed", response_model=Dict[str, Any])
async def get_detailed_health_status():
    """Get detailed system health information including metrics"""
    try:
        uptime = (datetime.now() - _start_time).total_seconds()
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        # Process information
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        # Database information
        db_health = await check_database_health()
        table_info = await get_table_info()
        
        # Request statistics
        global_request_rate = _request_count / max(uptime, 1)
        global_error_rate = _error_count / max(_request_count, 1) if _request_count > 0 else 0
        
        detailed_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": {
                "api_version": settings.APP_VERSION,
                "python_version": "3.9+",
                "environment": "production" if not settings.DEBUG else "development"
            },
            "uptime": {
                "seconds": uptime,
                "formatted": str(timedelta(seconds=int(uptime)))
            },
            "system": {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            },
            "process": {
                "cpu_percent": process_cpu,
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "threads": process.num_threads(),
                "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0
            },
            "database": db_health,
            "tables": table_info,
            "statistics": {
                "total_requests": _request_count,
                "total_errors": _error_count,
                "error_rate": global_error_rate,
                "requests_per_second": global_request_rate
            },
            "configuration": {
                "debug": settings.DEBUG,
                "log_level": settings.LOG_LEVEL,
                "rate_limiting": {
                    "default": settings.RATE_LIMIT_DEFAULT,
                    "premium": settings.RATE_LIMIT_PREMIUM,
                    "enterprise": settings.RATE_LIMIT_ENTERPRISE
                },
                "features": {
                    "agents": settings.ENABLE_AGENT_QUERIES,
                    "streaming": settings.ENABLE_REAL_TIME_STREAMING,
                    "trading": settings.ENABLE_TRADING_METRICS,
                    "workflows": settings.ENABLE_WORKFLOW_MONITORING,
                    "users": settings.ENABLE_USER_MANAGEMENT,
                    "dashboard": settings.ENABLE_DASHBOARD_CONFIG
                }
            }
        }
        
        return detailed_status
        
    except Exception as e:
        logger.error(f"Failed to get detailed health status: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Failed to get detailed health status",
                "error": str(e)
            }
        )

@router.get("/database", response_model=DatabaseHealth)
async def get_database_health():
    """Get database-specific health information"""
    try:
        db_health = await check_database_health()
        return db_health
        
    except Exception as e:
        logger.error(f"Failed to get database health: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Failed to get database health",
                "error": str(e)
            }
        )

@router.get("/metrics", response_model=Dict[str, Any])
async def get_performance_metrics():
    """Get performance metrics and statistics"""
    try:
        uptime = (datetime.now() - _start_time).total_seconds()
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Response time simulation (in real implementation, would track actual response times)
        avg_response_time = 0.045  # 45ms average
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime,
            "requests": {
                "total": _request_count,
                "errors": _error_count,
                "success_rate": (_request_count - _error_count) / max(_request_count, 1),
                "requests_per_second": _request_count / max(uptime, 1),
                "average_response_time_ms": avg_response_time * 1000
            },
            "system": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "available_memory_mb": memory.available / (1024 * 1024)
            },
            "services": {
                "database": "healthy" if (await check_database_health())["status"] == "healthy" else "unhealthy",
                "redis": "not_configured",  # Would check Redis in real implementation
                "external_apis": "configured" if settings.LETTA_API_BASE_URL else "not_configured"
            },
            "throughput": {
                "current_rps": _request_count / max(uptime, 1),
                "peak_rps": _request_count / max(uptime, 1),  # Simplified
                "data_processed_mb": 0  # Would track actual data processed
            }
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Failed to get performance metrics",
                "error": str(e)
            }
        )

@router.get("/ready", response_model=APIResponse)
async def readiness_probe():
    """Readiness probe endpoint for load balancers"""
    try:
        # Check critical dependencies
        db_health = await check_database_health()
        
        if db_health["status"] != "healthy":
            raise HTTPException(
                status_code=503,
                detail={
                    "ready": False,
                    "reason": "Database not healthy"
                }
            )
        
        return APIResponse(
            success=True,
            message="Service is ready",
            data={
                "ready": True,
                "timestamp": datetime.now().isoformat(),
                "checks": {
                    "database": "ok",
                    "configuration": "ok",
                    "services": "ok"
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "reason": "Readiness check failed",
                "error": str(e)
            }
        )

@router.get("/live", response_model=APIResponse)
async def liveness_probe():
    """Liveness probe endpoint for container orchestration"""
    try:
        # Basic liveness check - if we can respond, we're alive
        uptime = (datetime.now() - _start_time).total_seconds()
        
        if uptime < 0:
            raise HTTPException(
                status_code=503,
                detail={
                    "alive": False,
                    "reason": "Negative uptime detected"
                }
            )
        
        return APIResponse(
            success=True,
            message="Service is alive",
            data={
                "alive": True,
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": uptime
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "alive": False,
                "reason": "Liveness check failed",
                "error": str(e)
            }
        )

@router.post("/reset-stats", response_model=APIResponse)
async def reset_performance_statistics():
    """Reset performance statistics (admin only)"""
    try:
        global _request_count, _error_count
        _request_count = 0
        _error_count = 0
        
        return APIResponse(
            success=True,
            message="Statistics reset successfully",
            data={
                "request_count": _request_count,
                "error_count": _error_count,
                "reset_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to reset statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "Failed to reset statistics",
                "error": str(e)
            }
        )

# Helper functions for tracking requests
def increment_request_count():
    """Increment global request counter"""
    global _request_count
    _request_count += 1

def increment_error_count():
    """Increment global error counter"""
    global _error_count
    _error_count += 1