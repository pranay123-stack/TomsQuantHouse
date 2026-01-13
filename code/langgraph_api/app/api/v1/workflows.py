"""
Workflow execution endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from ...auth.auth_handler import auth_handler, get_current_user
from ...auth.auth_models import (
    User, WorkflowCreate, WorkflowUpdate, Workflow, 
    WorkflowExecutionRequest, WorkflowExecutionResponse, 
    BatchWorkflowExecutionRequest, APIResponse, PaginatedResponse
)
from ...services.workflow_service import WorkflowService
from ...core.database import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()
workflow_service = WorkflowService()

@router.post("/", response_model=Workflow)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new workflow"""
    try:
        workflow = await workflow_service.create_workflow(workflow_data, current_user.id)
        return workflow
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=PaginatedResponse)
async def list_workflows(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    current_user: User = Depends(get_current_user)
):
    """List user workflows with pagination and filtering"""
    try:
        workflows, total = await workflow_service.list_workflows(
            user_id=current_user.id,
            page=page,
            per_page=per_page,
            status=status,
            workflow_type=workflow_type
        )
        
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            items=workflows,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get workflow by ID"""
    try:
        workflow = await workflow_service.get_workflow(workflow_id, current_user.id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{workflow_id}", response_model=Workflow)
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update workflow"""
    try:
        workflow = await workflow_service.update_workflow(
            workflow_id, workflow_data, current_user.id
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete workflow"""
    try:
        success = await workflow_service.delete_workflow(workflow_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return APIResponse(message="Workflow deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    execution_request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Execute workflow (single execution)"""
    try:
        # Verify workflow exists and belongs to user
        workflow = await workflow_service.get_workflow(workflow_id, current_user.id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        execution_response = await workflow_service.execute_workflow(
            workflow_id, execution_request, current_user.id
        )
        
        # Schedule callback if provided
        if execution_request.callback_url and not execution_request.synchronous:
            background_tasks.add_task(
                _send_callback, 
                execution_request.callback_url, 
                execution_response.dict()
            )
        
        return execution_response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute/batch", response_model=List[WorkflowExecutionResponse])
async def execute_batch_workflows(
    batch_request: BatchWorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Execute multiple workflows in batch"""
    try:
        execution_responses = await workflow_service.execute_batch_workflows(
            batch_request, current_user.id
        )
        
        return execution_responses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute batch workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/cancel")
async def cancel_workflow_execution(
    workflow_id: str,
    execution_id: Optional[str] = Query(None, description="Specific execution to cancel"),
    current_user: User = Depends(get_current_user)
):
    """Cancel workflow execution"""
    try:
        success = await workflow_service.cancel_workflow(
            workflow_id, execution_id, current_user.id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Workflow execution not found")
        
        return APIResponse(message="Workflow execution cancelled successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/history")
async def get_workflow_history(
    workflow_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get workflow execution history"""
    try:
        history, total = await workflow_service.get_workflow_history(
            workflow_id, current_user.id, page, per_page
        )
        
        return PaginatedResponse(
            items=history,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/status", response_model=dict)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get workflow current status"""
    try:
        status = await workflow_service.get_workflow_status(workflow_id, current_user.id)
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/clone", response_model=Workflow)
async def clone_workflow(
    workflow_id: str,
    new_name: Optional[str] = Query(None, description="Name for cloned workflow"),
    current_user: User = Depends(get_current_user)
):
    """Clone an existing workflow"""
    try:
        cloned_workflow = await workflow_service.clone_workflow(
            workflow_id, new_name, current_user.id
        )
        if not cloned_workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return cloned_workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clone workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}/metrics")
async def get_workflow_metrics(
    workflow_id: str,
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    current_user: User = Depends(get_current_user)
):
    """Get workflow execution metrics"""
    try:
        metrics = await workflow_service.get_workflow_metrics(
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

@router.post("/validate")
async def validate_workflow_config(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_user)
):
    """Validate workflow configuration without creating"""
    try:
        validation_result = await workflow_service.validate_workflow_config(workflow_data)
        return validation_result
    except Exception as e:
        logger.error(f"Failed to validate workflow config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _send_callback(callback_url: str, result: dict):
    """Send workflow completion callback"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=result, timeout=10.0)
    except Exception as e:
        logger.error(f"Failed to send callback to {callback_url}: {e}")