"""
State management endpoints for workflow state persistence
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import logging

from ...auth.auth_handler import auth_handler, get_current_user
from ...auth.auth_models import (
    User, StateCreate, StateUpdate, State, APIResponse, PaginatedResponse
)
from ...services.state_service import StateService
from ...core.database import db_manager

logger = logging.getLogger(__name__)
router = APIRouter()
state_service = StateService()

@router.post("/", response_model=State)
async def create_state(
    state_data: StateCreate,
    current_user: User = Depends(get_current_user)
):
    """Create workflow state"""
    try:
        # Verify workflow belongs to user
        workflow = await state_service.verify_workflow_ownership(
            state_data.workflow_id, current_user.id
        )
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found or access denied")
        
        state = await state_service.create_state(state_data)
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=PaginatedResponse)
async def list_states(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    node_name: Optional[str] = Query(None, description="Filter by node name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """List workflow states with filtering and pagination"""
    try:
        states, total = await state_service.list_states(
            user_id=current_user.id,
            workflow_id=workflow_id,
            node_name=node_name,
            status=status,
            page=page,
            per_page=per_page
        )
        
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            items=states,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    except Exception as e:
        logger.error(f"Failed to list states: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{state_id}", response_model=State)
async def get_state(
    state_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get state by ID"""
    try:
        state = await state_service.get_state(state_id, current_user.id)
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow/{workflow_id}", response_model=List[State])
async def get_workflow_states(
    workflow_id: str,
    node_name: Optional[str] = Query(None, description="Filter by specific node"),
    latest_only: bool = Query(False, description="Get only latest state per node"),
    current_user: User = Depends(get_current_user)
):
    """Get all states for a workflow"""
    try:
        states = await state_service.get_workflow_states(
            workflow_id, current_user.id, node_name, latest_only
        )
        return states
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow states: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{state_id}", response_model=State)
async def update_state(
    state_id: str,
    state_data: StateUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update workflow state"""
    try:
        state = await state_service.update_state(state_id, state_data, current_user.id)
        if not state:
            raise HTTPException(status_code=404, detail="State not found or access denied")
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{state_id}")
async def delete_state(
    state_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete workflow state"""
    try:
        success = await state_service.delete_state(state_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="State not found or access denied")
        
        return APIResponse(message="State deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/workflow/{workflow_id}")
async def delete_workflow_states(
    workflow_id: str,
    confirm: bool = Query(False, description="Confirmation required"),
    current_user: User = Depends(get_current_user)
):
    """Delete all states for a workflow"""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400, 
                detail="Confirmation required to delete all workflow states"
            )
        
        count = await state_service.delete_workflow_states(workflow_id, current_user.id)
        
        return APIResponse(
            message=f"Deleted {count} states for workflow {workflow_id}",
            data={"deleted_count": count}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow states: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{state_id}/history")
async def get_state_history(
    state_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get state change history"""
    try:
        history = await state_service.get_state_history(state_id, current_user.id)
        if not history:
            raise HTTPException(status_code=404, detail="State not found")
        return {"state_id": state_id, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get state history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{state_id}/checkpoint")
async def create_checkpoint(
    state_id: str,
    checkpoint_name: Optional[str] = Query(None, description="Optional checkpoint name"),
    current_user: User = Depends(get_current_user)
):
    """Create a checkpoint of current state"""
    try:
        checkpoint = await state_service.create_checkpoint(
            state_id, checkpoint_name, current_user.id
        )
        if not checkpoint:
            raise HTTPException(status_code=404, detail="State not found or access denied")
        return checkpoint
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restore/{checkpoint_id}")
async def restore_from_checkpoint(
    checkpoint_id: str,
    workflow_id: Optional[str] = Query(None, description="Target workflow ID"),
    current_user: User = Depends(get_current_user)
):
    """Restore workflow state from checkpoint"""
    try:
        restored_state = await state_service.restore_from_checkpoint(
            checkpoint_id, workflow_id, current_user.id
        )
        if not restored_state:
            raise HTTPException(status_code=404, detail="Checkpoint not found or access denied")
        return restored_state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore from checkpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{state_id}/diff")
async def compare_states(
    state_id: str,
    other_state_id: str = Query(..., description="Other state ID to compare with"),
    current_user: User = Depends(get_current_user)
):
    """Compare two workflow states"""
    try:
        diff = await state_service.compare_states(
            state_id, other_state_id, current_user.id
        )
        if diff is None:
            raise HTTPException(status_code=404, detail="State not found or access denied")
        return diff
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare states: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{state_id}/export")
async def export_state(
    state_id: str,
    format: str = Query("json", description="Export format (json, yaml)"),
    current_user: User = Depends(get_current_user)
):
    """Export state to file"""
    try:
        export_data = await state_service.export_state(state_id, format, current_user.id)
        if not export_data:
            raise HTTPException(status_code=404, detail="State not found or access denied")
        return export_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import")
async def import_state(
    workflow_id: str,
    state_data: dict,
    node_name: str,
    import_format: str = Query("json", description="Import format"),
    current_user: User = Depends(get_current_user)
):
    """Import state from external data"""
    try:
        # Verify workflow ownership
        workflow = await state_service.verify_workflow_ownership(workflow_id, current_user.id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found or access denied")
        
        state = await state_service.import_state(
            workflow_id, node_name, state_data, import_format, current_user.id
        )
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow/{workflow_id}/latest", response_model=List[State])
async def get_latest_states_by_node(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get latest state for each node in workflow"""
    try:
        states = await state_service.get_latest_states_by_node(workflow_id, current_user.id)
        return states
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest states: {e}")
        raise HTTPException(status_code=500, detail=str(e))