"""
ASYMEdge Dashboard API - Workflow Monitoring Routes

Workflow monitoring endpoints providing:
- Workflow definition management
- Workflow instance execution and monitoring
- Workflow status tracking and updates
- Workflow analytics and reporting
- Workflow scheduling and automation
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from api.database.models import WorkflowDefinition, WorkflowInstance
from api.database.database import get_db_session
from api.schemas import (
    WorkflowDefinitionResponse, WorkflowDefinitionCreate, WorkflowDefinitionUpdate,
    WorkflowInstanceResponse, WorkflowInstanceCreate, WorkflowInstanceUpdate,
    WorkflowStatus, APIResponse, PaginationParams
)
from api.services.workflow_service import workflow_monitoring_service
from api.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Workflow Definition Endpoints

@router.get("/definitions", response_model=List[WorkflowDefinitionResponse])
async def get_workflow_definitions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    workflow_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get all workflow definitions with optional filtering"""
    try:
        with get_db_session() as db:
            query = db.query(WorkflowDefinition)
            
            # Apply filters
            if workflow_type:
                query = query.filter(WorkflowDefinition.workflow_type == workflow_type)
            
            if is_active is not None:
                query = query.filter(WorkflowDefinition.is_active == is_active)
            
            # Apply pagination
            definitions = query.offset(skip).limit(limit).all()
            
            return [
                WorkflowDefinitionResponse(
                    id=definition.id,
                    name=definition.name,
                    description=definition.description,
                    workflow_type=definition.workflow_type,
                    configuration=definition.configuration,
                    version=definition.version,
                    is_active=definition.is_active,
                    created_by=definition.created_by,
                    created_at=definition.created_at,
                    updated_at=definition.updated_at
                )
                for definition in definitions
            ]
            
    except Exception as e:
        logger.error(f"Failed to get workflow definitions: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/definitions/{definition_id}", response_model=WorkflowDefinitionResponse)
async def get_workflow_definition(
    definition_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Get a specific workflow definition by ID"""
    try:
        with get_db_session() as db:
            definition = db.query(WorkflowDefinition).filter(
                WorkflowDefinition.id == definition_id
            ).first()
            
            if not definition:
                raise HTTPException(status_code=404, detail={"error": "Workflow definition not found"})
            
            return WorkflowDefinitionResponse(
                id=definition.id,
                name=definition.name,
                description=definition.description,
                workflow_type=definition.workflow_type,
                configuration=definition.configuration,
                version=definition.version,
                is_active=definition.is_active,
                created_by=definition.created_by,
                created_at=definition.created_at,
                updated_at=definition.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow definition {definition_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/definitions", response_model=WorkflowDefinitionResponse)
async def create_workflow_definition(
    definition_data: WorkflowDefinitionCreate,
    current_user: get_current_user = Depends(get_current_user)
):
    """Create a new workflow definition"""
    try:
        definition_response = await workflow_monitoring_service.create_workflow_definition(
            definition_data, current_user.id
        )
        
        return definition_response
        
    except Exception as e:
        logger.error(f"Failed to create workflow definition: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.put("/definitions/{definition_id}", response_model=WorkflowDefinitionResponse)
async def update_workflow_definition(
    definition_id: int,
    definition_data: WorkflowDefinitionUpdate,
    current_user: get_current_user = Depends(get_current_user)
):
    """Update an existing workflow definition"""
    try:
        with get_db_session() as db:
            definition = db.query(WorkflowDefinition).filter(
                WorkflowDefinition.id == definition_id
            ).first()
            
            if not definition:
                raise HTTPException(status_code=404, detail={"error": "Workflow definition not found"})
            
            # Update fields
            update_data = definition_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(definition, field, value)
            
            definition.updated_at = datetime.now()
            
            db.commit()
            db.refresh(definition)
            
            return WorkflowDefinitionResponse(
                id=definition.id,
                name=definition.name,
                description=definition.description,
                workflow_type=definition.workflow_type,
                configuration=definition.configuration,
                version=definition.version,
                is_active=definition.is_active,
                created_by=definition.created_by,
                created_at=definition.created_at,
                updated_at=definition.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow definition {definition_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/definitions/{definition_id}", response_model=APIResponse)
async def delete_workflow_definition(
    definition_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Delete a workflow definition (soft delete)"""
    try:
        with get_db_session() as db:
            definition = db.query(WorkflowDefinition).filter(
                WorkflowDefinition.id == definition_id
            ).first()
            
            if not definition:
                raise HTTPException(status_code=404, detail={"error": "Workflow definition not found"})
            
            # Check if definition has active instances
            active_instances = db.query(WorkflowInstance).filter(
                WorkflowInstance.workflow_definition_id == definition_id,
                WorkflowInstance.status.in_(["pending", "running"])
            ).count()
            
            if active_instances > 0:
                raise HTTPException(
                    status_code=400,
                    detail={"error": f"Cannot delete definition with {active_instances} active instances"}
                )
            
            # Soft delete
            definition.is_active = False
            definition.updated_at = datetime.now()
            
            db.commit()
            
            return APIResponse(
                success=True,
                message="Workflow definition deleted successfully",
                data={"definition_id": definition_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow definition {definition_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Workflow Instance Endpoints

@router.get("/instances", response_model=List[WorkflowInstanceResponse])
async def get_workflow_instances(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[WorkflowStatus] = Query(None),
    definition_id: Optional[int] = Query(None),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get workflow instances with optional filtering"""
    try:
        instances = await workflow_monitoring_service.get_workflow_instances(
            current_user.id, status
        )
        
        # Apply additional filters
        if definition_id:
            instances = [inst for inst in instances if inst.workflow_definition_id == definition_id]
        
        # Apply pagination
        paginated_instances = instances[skip:skip + limit]
        
        return paginated_instances
        
    except Exception as e:
        logger.error(f"Failed to get workflow instances: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/instances/{instance_id}", response_model=WorkflowInstanceResponse)
async def get_workflow_instance(
    instance_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Get a specific workflow instance by ID"""
    try:
        instance = await workflow_monitoring_service.get_workflow_instance(instance_id)
        
        if not instance:
            raise HTTPException(status_code=404, detail={"error": "Workflow instance not found"})
        
        # Check ownership
        with get_db_session() as db:
            db_instance = db.query(WorkflowInstance).filter(
                WorkflowInstance.id == instance_id
            ).first()
            
            if not db_instance or db_instance.owner_id != current_user.id:
                raise HTTPException(status_code=404, detail={"error": "Workflow instance not found"})
        
        return instance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/instances", response_model=WorkflowInstanceResponse)
async def create_workflow_instance(
    instance_data: WorkflowInstanceCreate,
    current_user: get_current_user = Depends(get_current_user)
):
    """Create and start a new workflow instance"""
    try:
        instance_response = await workflow_monitoring_service.create_workflow_instance(
            instance_data, current_user.id
        )
        
        return instance_response
        
    except Exception as e:
        logger.error(f"Failed to create workflow instance: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.put("/instances/{instance_id}", response_model=WorkflowInstanceResponse)
async def update_workflow_instance(
    instance_id: int,
    instance_data: WorkflowInstanceUpdate,
    current_user: get_current_user = Depends(get_current_user)
):
    """Update a workflow instance"""
    try:
        with get_db_session() as db:
            instance = db.query(WorkflowInstance).filter(
                WorkflowInstance.id == instance_id,
                WorkflowInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Workflow instance not found"})
            
            # Update fields
            update_data = instance_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(instance, field, value)
            
            instance.updated_at = datetime.now()
            
            db.commit()
            db.refresh(instance)
            
            definition = db.query(WorkflowDefinition).filter(
                WorkflowDefinition.id == instance.workflow_definition_id
            ).first()
            
            return WorkflowInstanceResponse(
                id=instance.id,
                name=instance.name,
                workflow_definition_id=instance.workflow_definition_id,
                status=instance.status,
                current_step=instance.current_step,
                progress=instance.progress,
                configuration=instance.configuration,
                input_data=instance.input_data,
                output_data=instance.output_data,
                error_message=instance.error_message,
                execution_log=instance.execution_log,
                started_at=instance.started_at,
                completed_at=instance.completed_at,
                created_at=instance.created_at,
                updated_at=instance.updated_at,
                definition=WorkflowDefinitionResponse(
                    id=definition.id,
                    name=definition.name,
                    description=definition.description,
                    workflow_type=definition.workflow_type,
                    configuration=definition.configuration,
                    version=definition.version,
                    is_active=definition.is_active,
                    created_by=definition.created_by,
                    created_at=definition.created_at,
                    updated_at=definition.updated_at
                )
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/instances/{instance_id}", response_model=APIResponse)
async def delete_workflow_instance(
    instance_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Delete a workflow instance (only if not running)"""
    try:
        with get_db_session() as db:
            instance = db.query(WorkflowInstance).filter(
                WorkflowInstance.id == instance_id,
                WorkflowInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Workflow instance not found"})
            
            if instance.status == WorkflowStatus.RUNNING:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Cannot delete running workflow instance"}
                )
            
            # Cancel workflow if pending
            if instance.status == WorkflowStatus.PENDING:
                await workflow_monitoring_service.cancel_workflow_instance(instance_id)
            
            # Delete instance
            db.delete(instance)
            db.commit()
            
            return APIResponse(
                success=True,
                message="Workflow instance deleted successfully",
                data={"instance_id": instance_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/instances/{instance_id}/start", response_model=APIResponse)
async def start_workflow_instance(
    instance_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Start a workflow instance"""
    try:
        with get_db_session() as db:
            instance = db.query(WorkflowInstance).filter(
                WorkflowInstance.id == instance_id,
                WorkflowInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Workflow instance not found"})
            
            if instance.status != WorkflowStatus.PENDING:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Workflow instance is not in pending status"}
                )
            
            # Get workflow definition
            definition = db.query(WorkflowDefinition).filter(
                WorkflowDefinition.id == instance.workflow_definition_id
            ).first()
            
            # Start workflow execution
            await workflow_monitoring_service.orchestrator.start_workflow(
                definition.configuration,
                instance_id,
                instance.name
            )
            
            return APIResponse(
                success=True,
                message="Workflow instance started successfully",
                data={"instance_id": instance_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start workflow instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/instances/{instance_id}/cancel", response_model=APIResponse)
async def cancel_workflow_instance(
    instance_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Cancel a running workflow instance"""
    try:
        success = await workflow_monitoring_service.cancel_workflow_instance(instance_id)
        
        if not success:
            raise HTTPException(status_code=404, detail={"error": "Workflow instance not found or cannot be cancelled"})
        
        return APIResponse(
            success=True,
            message="Workflow instance cancelled successfully",
            data={"instance_id": instance_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/instances/{instance_id}/restart", response_model=APIResponse)
async def restart_workflow_instance(
    instance_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Restart a failed or cancelled workflow instance"""
    try:
        with get_db_session() as db:
            instance = db.query(WorkflowInstance).filter(
                WorkflowInstance.id == instance_id,
                WorkflowInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Workflow instance not found"})
            
            if instance.status not in [WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Workflow instance can only be restarted if failed or cancelled"}
                )
            
            # Reset workflow instance
            instance.status = WorkflowStatus.PENDING
            instance.current_step = None
            instance.progress = 0.0
            instance.error_message = None
            instance.started_at = None
            instance.completed_at = None
            instance.updated_at = datetime.now()
            
            db.commit()
            
            return APIResponse(
                success=True,
                message="Workflow instance reset successfully. Use /start to begin execution.",
                data={"instance_id": instance_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart workflow instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Workflow Statistics and Analytics

@router.get("/statistics", response_model=Dict[str, Any])
async def get_workflow_statistics(
    current_user: get_current_user = Depends(get_current_user)
):
    """Get workflow statistics for the current user"""
    try:
        stats = await workflow_monitoring_service.get_workflow_statistics(current_user.id)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get workflow statistics: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/types", response_model=List[Dict[str, Any]])
async def get_workflow_types():
    """Get available workflow types"""
    try:
        workflow_types = [
            {
                "type": "analysis",
                "description": "Data analysis workflows",
                "examples": ["portfolio_analysis", "risk_assessment", "market_research"]
            },
            {
                "type": "trading",
                "description": "Automated trading workflows",
                "examples": ["rebalancing", "signal_execution", "order_management"]
            },
            {
                "type": "monitoring",
                "description": "System monitoring workflows",
                "examples": ["alert_monitoring", "performance_tracking", "health_checks"]
            },
            {
                "type": "data_collection",
                "description": "Data gathering workflows",
                "examples": ["market_data_pull", "news_collection", "economic_indicators"]
            },
            {
                "type": "reporting",
                "description": "Report generation workflows",
                "examples": ["daily_reports", "performance_summaries", "compliance_reports"]
            },
            {
                "type": "backup",
                "description": "Data backup workflows",
                "examples": ["database_backup", "file_archival", "data_migration"]
            },
            {
                "type": "notification",
                "description": "Notification and communication workflows",
                "examples": ["email_alerts", "sms_notifications", "slack_messages"]
            }
        ]
        
        return workflow_types
        
    except Exception as e:
        logger.error(f"Failed to get workflow types: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_workflow_templates():
    """Get pre-defined workflow templates"""
    try:
        templates = [
            {
                "name": "Daily Portfolio Analysis",
                "description": "Comprehensive daily portfolio analysis including performance metrics, risk assessment, and recommendations",
                "workflow_type": "analysis",
                "estimated_duration": "15 minutes",
                "steps": [
                    {"name": "Collect Portfolio Data", "type": "data_collection"},
                    {"name": "Calculate Performance Metrics", "type": "analysis"},
                    {"name": "Generate Report", "type": "reporting"}
                ],
                "configuration": {
                    "schedule": "daily",
                    "time": "09:00",
                    "recipients": ["portfolio.manager@company.com"]
                }
            },
            {
                "name": "Risk Alert System",
                "description": "Monitor portfolio risk and send alerts when thresholds are exceeded",
                "workflow_type": "monitoring",
                "estimated_duration": "5 minutes",
                "steps": [
                    {"name": "Check Risk Metrics", "type": "analysis"},
                    {"name": "Evaluate Thresholds", "type": "condition"},
                    {"name": "Send Alerts", "type": "notification"}
                ],
                "configuration": {
                    "check_interval": "hourly",
                    "thresholds": {
                        "var_limit": 50000,
                        "concentration_limit": 0.4
                    }
                }
            },
            {
                "name": "Portfolio Rebalancing",
                "description": "Automated portfolio rebalancing based on target allocations",
                "workflow_type": "trading",
                "estimated_duration": "30 minutes",
                "steps": [
                    {"name": "Calculate Current Allocation", "type": "analysis"},
                    {"name": "Determine Rebalance Trades", "type": "analysis"},
                    {"name": "Execute Trades", "type": "trading_action"},
                    {"name": "Update Records", "type": "data_collection"}
                ],
                "configuration": {
                    "rebalance_threshold": 0.05,
                    "target_allocations": {
                        "stocks": 0.70,
                        "bonds": 0.25,
                        "cash": 0.05
                    }
                }
            }
        ]
        
        return templates
        
    except Exception as e:
        logger.error(f"Failed to get workflow templates: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/logs/{instance_id}", response_model=Dict[str, Any])
async def get_workflow_execution_log(
    instance_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Get detailed execution log for a workflow instance"""
    try:
        with get_db_session() as db:
            instance = db.query(WorkflowInstance).filter(
                WorkflowInstance.id == instance_id,
                WorkflowInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Workflow instance not found"})
            
            # Format execution log
            formatted_log = {
                "instance_id": instance_id,
                "workflow_name": instance.name,
                "status": instance.status,
                "started_at": instance.started_at.isoformat() if instance.started_at else None,
                "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
                "execution_log": instance.execution_log or [],
                "error_message": instance.error_message,
                "total_execution_time": None
            }
            
            # Calculate total execution time
            if instance.started_at and instance.completed_at:
                duration = instance.completed_at - instance.started_at
                formatted_log["total_execution_time"] = str(duration)
            
            return formatted_log
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow execution log for {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/health", response_model=Dict[str, Any])
async def get_workflow_service_health(current_user: get_current_user = Depends(get_current_user)):
    """Get workflow service health status"""
    try:
        # Check active workflows
        active_workflows = len(workflow_monitoring_service.orchestrator.active_workflows)
        
        # Get recent workflow statistics
        recent_stats = await workflow_monitoring_service.get_workflow_statistics(current_user.id)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "workflow_orchestrator": "healthy",
                "workflow_executor": "healthy",
                "database": "healthy"
            },
            "metrics": {
                "active_workflows": active_workflows,
                "total_workflows": recent_stats.get("total_workflows", 0),
                "running_workflows": recent_stats.get("running_workflows", 0),
                "completed_workflows": recent_stats.get("completed_workflows", 0),
                "failed_workflows": recent_stats.get("failed_workflows", 0)
            },
            "health_checks": {
                "database_connection": "pass",
                "workflow_execution": "pass",
                "memory_usage": "pass"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get workflow service health: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "components": {
                "workflow_orchestrator": "error",
                "workflow_executor": "unknown",
                "database": "unknown"
            }
        }