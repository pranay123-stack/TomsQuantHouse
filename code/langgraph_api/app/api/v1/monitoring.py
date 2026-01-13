"""
Monitoring endpoints for system health and performance metrics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from ...auth.auth_handler import auth_handler, get_current_user, auth_handler
from ...auth.auth_models import User, HealthStatus, MetricsData, APIResponse
from ...services.monitoring_service import MonitoringService
from ...services.health_monitor import HealthMonitor

logger = logging.getLogger(__name__)
router = APIRouter()
monitoring_service = MonitoringService()
health_monitor = HealthMonitor()

@router.get("/health", response_model=HealthStatus)
async def get_system_health(
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive system health status"""
    try:
        health_status = await health_monitor.get_comprehensive_health()
        return HealthStatus(**health_status)
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health/{workflow_id}")
async def get_workflow_health(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get health status for specific workflow"""
    try:
        health_data = await monitoring_service.get_workflow_health(workflow_id, current_user.id)
        if not health_data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return health_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=Dict[str, Any])
async def get_system_metrics(
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    current_user: User = Depends(get_current_user)
):
    """Get system performance metrics"""
    try:
        metrics = await monitoring_service.get_system_metrics(time_range_hours)
        return metrics
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/workflow/{workflow_id}")
async def get_workflow_metrics(
    workflow_id: str,
    time_range_hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user)
):
    """Get metrics for specific workflow"""
    try:
        metrics = await monitoring_service.get_workflow_metrics(
            workflow_id, current_user.id, time_range_hours
        )
        if not metrics:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts", response_model=List[Dict[str, Any]])
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity (critical, high, medium, low)"),
    resolved: bool = Query(False, description="Include resolved alerts"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of alerts"),
    current_user: User = Depends(get_current_user)
):
    """Get active system alerts"""
    try:
        alerts = await monitoring_service.get_alerts(
            user_id=current_user.id,
            severity=severity,
            resolved=resolved,
            limit=limit
        )
        return alerts
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    current_user: User = Depends(auth_handler.require_permission("monitoring.manage"))
):
    """Mark alert as resolved"""
    try:
        success = await monitoring_service.resolve_alert(alert_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return APIResponse(message="Alert resolved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_performance_summary(
    time_range_hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user)
):
    """Get performance summary across all workflows"""
    try:
        summary = await monitoring_service.get_performance_summary(
            user_id=current_user.id,
            time_range_hours=time_range_hours
        )
        return summary
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/throughput")
async def get_throughput_metrics(
    time_range_hours: int = Query(24, ge=1, le=168),
    interval_minutes: int = Query(60, ge=5, le=1440, description="Aggregation interval"),
    current_user: User = Depends(get_current_user)
):
    """Get workflow throughput metrics"""
    try:
        throughput = await monitoring_service.get_throughput_metrics(
            user_id=current_user.id,
            time_range_hours=time_range_hours,
            interval_minutes=interval_minutes
        )
        return throughput
    except Exception as e:
        logger.error(f"Failed to get throughput metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors")
async def get_error_analysis(
    time_range_hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of errors"),
    current_user: User = Depends(get_current_user)
):
    """Get error analysis and patterns"""
    try:
        error_analysis = await monitoring_service.get_error_analysis(
            user_id=current_user.id,
            time_range_hours=time_range_hours,
            limit=limit
        )
        return error_analysis
    except Exception as e:
        logger.error(f"Failed to get error analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources")
async def get_resource_utilization(
    current_user: User = Depends(get_current_user)
):
    """Get system resource utilization"""
    try:
        resources = await monitoring_service.get_resource_utilization()
        return resources
    except Exception as e:
        logger.error(f"Failed to get resource utilization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def get_performance_trends(
    time_range_hours: int = Query(168, ge=24, le=720, description="30 days max"),
    current_user: User = Depends(get_current_user)
):
    """Get long-term performance trends"""
    try:
        trends = await monitoring_service.get_performance_trends(
            user_id=current_user.id,
            time_range_hours=time_range_hours
        )
        return trends
    except Exception as e:
        logger.error(f"Failed to get performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/cleanup")
async def cleanup_expired_data(
    data_types: Optional[List[str]] = Query(None, description="Types of data to clean up"),
    dry_run: bool = Query(True, description="Preview cleanup without actually deleting"),
    current_user: User = Depends(auth_handler.require_permission("system.admin"))
):
    """Clean up expired monitoring data"""
    try:
        cleanup_result = await monitoring_service.cleanup_expired_data(
            user_id=current_user.id,
            data_types=data_types,
            dry_run=dry_run
        )
        return cleanup_result
    except Exception as e:
        logger.error(f"Failed to cleanup expired data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboards/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user)
):
    """Get dashboard summary data for monitoring UI"""
    try:
        summary = await monitoring_service.get_dashboard_summary(current_user.id)
        return summary
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboards/workflow/{workflow_id}")
async def get_workflow_dashboard_data(
    workflow_id: str,
    time_range_hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user)
):
    """Get workflow-specific dashboard data"""
    try:
        dashboard_data = await monitoring_service.get_workflow_dashboard_data(
            workflow_id, current_user.id, time_range_hours
        )
        if not dashboard_data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return dashboard_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/checks/comprehensive")
async def run_comprehensive_health_check(
    current_user: User = Depends(auth_handler.require_permission("monitoring.manage"))
):
    """Run comprehensive system health check"""
    try:
        health_check = await monitoring_service.run_comprehensive_health_check()
        return health_check
    except Exception as e:
        logger.error(f"Failed to run comprehensive health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/test")
async def test_notification_system(
    notification_type: str = Query(..., description="Type of notification to test"),
    current_user: User = Depends(auth_handler.require_permission("monitoring.manage"))
):
    """Test notification system"""
    try:
        result = await monitoring_service.test_notification_system(
            notification_type, current_user.id
        )
        return result
    except Exception as e:
        logger.error(f"Failed to test notification system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compliance")
async def get_compliance_report(
    time_range_hours: int = Query(168, ge=24, le=720),
    current_user: User = Depends(auth_handler.require_permission("system.admin"))
):
    """Get system compliance report"""
    try:
        compliance_report = await monitoring_service.get_compliance_report(
            user_id=current_user.id,
            time_range_hours=time_range_hours
        )
        return compliance_report
    except Exception as e:
        logger.error(f"Failed to get compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))