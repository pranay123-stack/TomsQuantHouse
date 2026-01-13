"""
Workflow Execution API
FastAPI-based REST API for workflow execution and management
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import uuid
import logging
from datetime import datetime
import asyncio

from ..workflows.trading_workflow import TradingWorkflow
from ..checkpoints.redis_checkpointer import RedisCheckpointer
from ..visualization.monitoring import WorkflowVisualization, WorkflowMonitoring

logger = logging.getLogger(__name__)

# =============================================================================
# API MODELS
# =============================================================================

class WorkflowRequest(BaseModel):
    """Request model for workflow execution"""
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    strategy: str = Field(default="default", description="Trading strategy to use")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    auto_checkpoint: bool = Field(default=True, description="Enable automatic checkpointing")
    callback_url: Optional[str] = Field(default=None, description="Callback URL for completion")

class BatchWorkflowRequest(BaseModel):
    """Request model for batch workflow execution"""
    workflows: List[WorkflowRequest] = Field(..., description="List of workflow requests")
    max_concurrent: int = Field(default=5, description="Maximum concurrent executions")

class WorkflowResponse(BaseModel):
    """Response model for workflow execution"""
    workflow_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    timestamp: str

class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status"""
    workflow_id: str
    status: str
    symbol: Optional[str] = None
    strategy: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    current_node: Optional[str] = None
    execution_history: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

class WorkflowResultsResponse(BaseModel):
    """Response model for workflow results"""
    workflow_id: str
    status: str
    final_decision: Optional[str] = None
    confidence: Optional[float] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None

class SystemHealthResponse(BaseModel):
    """Response model for system health"""
    status: str
    timestamp: str
    redis_connection: bool
    active_workflows: int
    recent_metrics: Dict[str, Any]
    components: Dict[str, str]

# =============================================================================
# API INITIALIZATION
# =============================================================================

def create_workflow_api(
    trading_workflow: TradingWorkflow,
    redis_checkpointer: RedisCheckpointer
) -> FastAPI:
    """
    Create and configure the workflow API
    
    Args:
        trading_workflow: Trading workflow manager instance
        redis_checkpointer: Redis checkpointer instance
        
    Returns:
        FastAPI: Configured API instance
    """
    # Create FastAPI app
    app = FastAPI(
        title="LangGraph Trading Workflow API",
        description="Comprehensive API for trading workflow execution with Redis checkpointing",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize monitoring components
    workflow_viz = WorkflowVisualization(redis_checkpointer)
    workflow_monitor = WorkflowMonitoring(redis_checkpointer)
    
    # =============================================================================
    # HEALTH AND SYSTEM ENDPOINTS
    # =============================================================================
    
    @app.get("/health", response_model=SystemHealthResponse)
    async def health_check():
        """System health check"""
        try:
            health_data = trading_workflow.health_check()
            return SystemHealthResponse(**health_data)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/system/overview")
    async def get_system_overview():
        """Get comprehensive system overview"""
        try:
            overview = workflow_monitor.get_system_overview()
            return JSONResponse(content=overview)
        except Exception as e:
            logger.error(f"System overview failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/system/metrics")
    async def get_system_metrics(time_range_hours: int = 24):
        """Get system metrics"""
        try:
            metrics = trading_workflow.get_workflow_metrics(time_range_hours)
            return JSONResponse(content=metrics)
        except Exception as e:
            logger.error(f"System metrics failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =============================================================================
    # WORKFLOW EXECUTION ENDPOINTS
    # =============================================================================
    
    @app.post("/api/v1/workflows/execute", response_model=WorkflowResponse)
    async def execute_workflow(
        request: WorkflowRequest,
        background_tasks: BackgroundTasks
    ):
        """Execute a trading workflow"""
        try:
            # Execute workflow
            result = trading_workflow.execute_trading_workflow(
                symbol=request.symbol,
                strategy=request.strategy,
                metadata=request.metadata,
                auto_checkpoint=request.auto_checkpoint,
                callback_url=request.callback_url
            )
            
            # Schedule background cleanup if needed
            if request.callback_url:
                background_tasks.add_task(
                    _send_callback, 
                    request.callback_url, 
                    result
                )
            
            return WorkflowResponse(**result)
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/workflows/batch", response_model=List[WorkflowResponse])
    async def execute_batch_workflows(request: BatchWorkflowRequest):
        """Execute multiple workflows in batch"""
        try:
            # Convert request models to dictionaries
            workflow_requests = [
                {
                    "symbol": wf.symbol,
                    "strategy": wf.strategy,
                    "metadata": wf.metadata,
                    "auto_checkpoint": wf.auto_checkpoint,
                    "callback_url": wf.callback_url
                }
                for wf in request.workflows
            ]
            
            # Execute batch
            results = trading_workflow.batch_execute_workflows(
                workflow_requests=workflow_requests,
                max_concurrent=request.max_concurrent
            )
            
            return [WorkflowResponse(**result) for result in results]
            
        except Exception as e:
            logger.error(f"Batch workflow execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =============================================================================
    # WORKFLOW MANAGEMENT ENDPOINTS
    # =============================================================================
    
    @app.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
    async def get_workflow_status(workflow_id: str):
        """Get workflow status"""
        try:
            status = trading_workflow.get_workflow_status(workflow_id)
            if not status:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            return WorkflowStatusResponse(**status)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get workflow status failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/workflows/{workflow_id}/results", response_model=WorkflowResultsResponse)
    async def get_workflow_results(
        workflow_id: str, 
        include_intermediate: bool = False
    ):
        """Get workflow results"""
        try:
            results = trading_workflow.get_workflow_results(
                workflow_id, 
                include_intermediate=include_intermediate
            )
            if not results:
                raise HTTPException(status_code=404, detail="Workflow results not found")
            
            return WorkflowResultsResponse(**results)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get workflow results failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/workflows/{workflow_id}/history")
    async def get_workflow_history(workflow_id: str):
        """Get workflow execution history"""
        try:
            history = trading_workflow.get_workflow_history(workflow_id)
            return JSONResponse(content={"workflow_id": workflow_id, "history": history})
            
        except Exception as e:
            logger.error(f"Get workflow history failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/workflows")
    async def list_workflows(
        status_filter: Optional[str] = None,
        limit: int = 50,
        sort_by: str = "timestamp"
    ):
        """List workflows with filtering"""
        try:
            workflows = trading_workflow.list_workflows(
                status_filter=status_filter,
                limit=limit,
                sort_by=sort_by
            )
            return JSONResponse(content={
                "workflows": workflows,
                "count": len(workflows)
            })
            
        except Exception as e:
            logger.error(f"List workflows failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/workflows/{workflow_id}/cancel")
    async def cancel_workflow(workflow_id: str, reason: Optional[str] = None):
        """Cancel a running workflow"""
        try:
            success = trading_workflow.cancel_workflow(workflow_id, reason)
            if not success:
                raise HTTPException(status_code=404, detail="Workflow not found or cannot be cancelled")
            
            return JSONResponse(content={
                "workflow_id": workflow_id,
                "status": "cancelled",
                "message": "Workflow cancelled successfully"
            })
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cancel workflow failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/v1/workflows/{workflow_id}")
    async def delete_workflow(workflow_id: str):
        """Delete workflow and all associated data"""
        try:
            success = trading_workflow.delete_workflow(workflow_id)
            if not success:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            return JSONResponse(content={
                "workflow_id": workflow_id,
                "status": "deleted",
                "message": "Workflow deleted successfully"
            })
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Delete workflow failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/workflows/{checkpoint_id}/resume")
    async def resume_workflow(checkpoint_id: str):
        """Resume workflow from checkpoint"""
        try:
            result = trading_workflow.resume_workflow(checkpoint_id)
            return JSONResponse(content=result)
            
        except Exception as e:
            logger.error(f"Resume workflow failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =============================================================================
    # VISUALIZATION ENDPOINTS
    # =============================================================================
    
    @app.get("/api/v1/visualization/graph/{workflow_id}")
    async def get_workflow_graph(workflow_id: Optional[str] = None):
        """Get workflow graph visualization (Mermaid format)"""
        try:
            mermaid_code = workflow_viz.generate_workflow_graph_mermaid(workflow_id=workflow_id)
            return JSONResponse(content={"graph": mermaid_code})
            
        except Exception as e:
            logger.error(f"Workflow graph generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/visualization/timeline/{workflow_id}")
    async def get_workflow_timeline(workflow_id: str):
        """Get workflow timeline visualization (Mermaid format)"""
        try:
            timeline = workflow_viz.generate_workflow_timeline(workflow_id)
            return JSONResponse(content={"timeline": timeline})
            
        except Exception as e:
            logger.error(f"Workflow timeline generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/visualization/metrics")
    async def get_execution_metrics(time_range_hours: int = 24):
        """Get execution metrics for visualization"""
        try:
            metrics = workflow_viz.generate_execution_metrics_chart(time_range_hours)
            return JSONResponse(content=metrics)
            
        except Exception as e:
            logger.error(f"Execution metrics generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =============================================================================
    # MONITORING ENDPOINTS
    # =============================================================================
    
    @app.get("/api/v1/monitoring/status")
    async def get_real_time_status():
        """Get real-time workflow status"""
        try:
            status = workflow_monitor.get_real_time_status()
            return JSONResponse(content=status)
            
        except Exception as e:
            logger.error(f"Real-time status failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/monitoring/health/{workflow_id}")
    async def get_workflow_health(workflow_id: str):
        """Get workflow health assessment"""
        try:
            health = workflow_monitor.get_workflow_health(workflow_id)
            return JSONResponse(content=health)
            
        except Exception as e:
            logger.error(f"Workflow health assessment failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/v1/maintenance/cleanup")
    async def cleanup_expired_workflows(max_age_hours: int = 24):
        """Clean up expired workflows"""
        try:
            cleaned_count = trading_workflow.cleanup_expired_workflows(max_age_hours)
            return JSONResponse(content={
                "cleaned_count": cleaned_count,
                "message": f"Cleaned up {cleaned_count} expired workflows"
            })
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # =============================================================================
    # HELPER FUNCTIONS
    # =============================================================================
    
    async def _send_callback(callback_url: str, result: Dict[str, Any]):
        """Send workflow completion callback"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(callback_url, json=result) as response:
                    if response.status == 200:
                        logger.info(f"Callback sent successfully to {callback_url}")
                    else:
                        logger.warning(f"Callback failed: {response.status}")
        except Exception as e:
            logger.error(f"Failed to send callback: {e}")
    
    return app

# =============================================================================
# STANDALONE API SERVER
# =============================================================================

def run_api_server(
    trading_workflow: TradingWorkflow,
    redis_checkpointer: RedisCheckpointer,
    host: str = "0.0.0.0",
    port: int = 8000,
    debug: bool = False
):
    """
    Run the workflow API server
    
    Args:
        trading_workflow: Trading workflow manager instance
        redis_checkpointer: Redis checkpointer instance
        host: API server host
        port: API server port
        debug: Enable debug mode
    """
    import uvicorn
    
    # Create API
    app = create_workflow_api(trading_workflow, redis_checkpointer)
    
    # Run server
    logger.info(f"Starting workflow API server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info" if not debug else "debug",
        reload=debug
    )

if __name__ == "__main__":
    # Example usage
    import uvicorn
    from ..checkpoints.redis_checkpointer import RedisCheckpointer
    from ..workflows.trading_workflow import TradingWorkflow
    
    # This would be initialized with actual Redis client
    # redis_checkpointer = RedisCheckpointer(redis_client)
    # trading_workflow = TradingWorkflow(redis_checkpointer)
    
    # Run the API server
    # run_api_server(trading_workflow, redis_checkpointer)
    
    print("Workflow API server module loaded")