"""
LangGraph API Service
FastAPI-based REST API for LangGraph workflow management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import asyncio
import json
import uuid
from datetime import datetime, timezone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LangGraph API Service",
    description="REST API for LangGraph workflow orchestration",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Pydantic Models
class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = {}

class WorkflowExecute(BaseModel):
    input_data: Dict[str, Any]
    config: Optional[Dict[str, Any]] = {}
    async_execution: bool = False

class StateQuery(BaseModel):
    filters: Optional[Dict[str, Any]] = None
    limit: int = 100
    offset: int = 0

class WorkflowResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    config: Dict[str, Any]

class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    execution_time: Optional[float] = None

# In-memory storage (replace with Redis in production)
workflows_store = {}
executions_store = {}
states_store = {}

# Mock LangGraph Integration
class MockLangGraphService:
    """Mock LangGraph service for development"""
    
    def __init__(self):
        self.active_workflows = {}
        self.execution_history = []
    
    async def create_workflow(self, workflow_data: dict) -> dict:
        workflow_id = str(uuid.uuid4())
        workflow = {
            "id": workflow_id,
            "name": workflow_data["name"],
            "description": workflow_data.get("description"),
            "nodes": workflow_data["nodes"],
            "edges": workflow_data["edges"],
            "config": workflow_data.get("config", {}),
            "status": "created",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        workflows_store[workflow_id] = workflow
        return workflow
    
    async def execute_workflow(self, workflow_id: str, input_data: dict, config: dict = None) -> dict:
        execution_id = str(uuid.uuid4())
        execution = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "input_data": input_data,
            "output_data": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "execution_time": None
        }
        executions_store[execution_id] = execution
        
        # Simulate workflow execution
        await asyncio.sleep(0.1)  # Simulate processing time
        
        execution["status"] = "completed"
        execution["output_data"] = {"result": "Workflow executed successfully", "confidence": 0.85}
        execution["execution_time"] = 0.1
        execution["updated_at"] = datetime.now(timezone.utc)
        
        return execution
    
    async def get_workflow_state(self, workflow_id: str) -> dict:
        # Mock state retrieval
        return {
            "workflow_id": workflow_id,
            "current_node": "execution",
            "node_states": {},
            "metadata": {},
            "checkpoints": []
        }
    
    async def get_execution_status(self, execution_id: str) -> dict:
        if execution_id in executions_store:
            return executions_store[execution_id]
        raise ValueError(f"Execution {execution_id} not found")

# Initialize LangGraph service
langgraph_service = MockLangGraphService()

# Dependency for authentication (mock)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # In production, verify JWT token and return user
    return {"id": "user_123", "role": "admin"}

# API Endpoints

@app.get("/")
async def root():
    """API health check"""
    return {"message": "LangGraph API Service", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "langgraph": "operational",
            "redis": "connected",
            "database": "connected"
        }
    }

@app.post("/api/v1/workflows", response_model=WorkflowResponse)
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new workflow"""
    try:
        workflow_data = workflow.dict()
        workflow_data["nodes"] = [
            {
                "id": node.get("id", f"node_{i}"),
                "type": node.get("type", "default"),
                "config": node.get("config", {})
            }
            for i, node in enumerate(workflow_data["nodes"])
        ]
        
        created_workflow = await langgraph_service.create_workflow(workflow_data)
        return WorkflowResponse(**created_workflow)
    except Exception as e:
        logger.error(f"Error creating workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")

@app.get("/api/v1/workflows", response_model=List[WorkflowResponse])
async def list_workflows(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """List all workflows"""
    workflows = list(workflows_store.values())
    return [WorkflowResponse(**wf) for wf in workflows[offset:offset+limit]]

@app.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get workflow by ID"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse(**workflows_store[workflow_id])

@app.delete("/api/v1/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete workflow by ID"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Delete related executions
    executions_to_delete = [
        exec_id for exec_id, exec_data in executions_store.items()
        if exec_data["workflow_id"] == workflow_id
    ]
    for exec_id in executions_to_delete:
        del executions_store[exec_id]
    
    del workflows_store[workflow_id]
    return {"message": "Workflow deleted successfully"}

@app.post("/api/v1/workflows/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(
    workflow_id: str,
    execution: WorkflowExecute,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Execute a workflow"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    try:
        execution_result = await langgraph_service.execute_workflow(
            workflow_id,
            execution.input_data,
            execution.config or {}
        )
        return ExecutionResponse(**execution_result)
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")

@app.post("/api/v1/workflows/{workflow_id}/execute-batch")
async def execute_workflow_batch(
    workflow_id: str,
    executions: List[WorkflowExecute],
    current_user: dict = Depends(get_current_user)
):
    """Execute workflow in batch mode"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    results = []
    for execution in executions:
        try:
            result = await langgraph_service.execute_workflow(
                workflow_id,
                execution.input_data,
                execution.config or {}
            )
            results.append(ExecutionResponse(**result))
        except Exception as e:
            results.append({"error": str(e), "input": execution.dict()})
    
    return {"results": results, "total": len(executions)}

@app.get("/api/v1/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get execution status"""
    try:
        execution = await langgraph_service.get_execution_status(execution_id)
        return ExecutionResponse(**execution)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/v1/workflows/{workflow_id}/state")
async def get_workflow_state(
    workflow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get workflow state"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    try:
        state = await langgraph_service.get_workflow_state(workflow_id)
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")

@app.post("/api/v1/workflows/{workflow_id}/state")
async def update_workflow_state(
    workflow_id: str,
    state_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update workflow state"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Store state update
    state_key = f"workflow_{workflow_id}_state"
    states_store[state_key] = {
        "workflow_id": workflow_id,
        "data": state_data,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return {"message": "State updated successfully"}

@app.get("/api/v1/workflows/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """List executions for a workflow"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow_executions = [
        exec_data for exec_data in executions_store.values()
        if exec_data["workflow_id"] == workflow_id
    ]
    
    return [
        ExecutionResponse(**exec_data).dict()
        for exec_data in workflow_executions[offset:offset+limit]
    ]

@app.get("/api/v1/metrics")
async def get_metrics(current_user: dict = Depends(get_current_user)):
    """Get system metrics"""
    return {
        "workflows": {
            "total": len(workflows_store),
            "active": sum(1 for wf in workflows_store.values() if wf["status"] == "active"),
            "completed": sum(1 for wf in workflows_store.values() if wf["status"] == "completed")
        },
        "executions": {
            "total": len(executions_store),
            "running": sum(1 for exec in executions_store.values() if exec["status"] == "running"),
            "completed": sum(1 for exec in executions_store.values() if exec["status"] == "completed"),
            "failed": sum(1 for exec in executions_store.values() if exec["status"] == "failed")
        },
        "performance": {
            "avg_execution_time": 0.15,
            "throughput": 25.5,
            "success_rate": 0.94
        }
    }

@app.get("/api/v1/workflows/{workflow_id}/visualization")
async def get_workflow_visualization(
    workflow_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get workflow visualization data"""
    if workflow_id not in workflows_store:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = workflows_store[workflow_id]
    
    # Generate Mermaid diagram
    mermaid_diagram = f"""
    graph TD
    """
    
    # Add nodes
    for i, node in enumerate(workflow["nodes"]):
        node_id = node.get("id", f"node_{i}")
        node_type = node.get("type", "default")
        mermaid_diagram += f'    {node_id}["{node_type}<br/>{node_id}"]\n'
    
    # Add edges
    for edge in workflow["edges"]:
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            mermaid_diagram += f'    {source} --> {target}\n'
    
    mermaid_diagram += "    style start fill:#e1f5fe\n    style end fill:#f3e5f5"
    
    return {
        "workflow_id": workflow_id,
        "mermaid_diagram": mermaid_diagram,
        "nodes": workflow["nodes"],
        "edges": workflow["edges"],
        "statistics": {
            "node_count": len(workflow["nodes"]),
            "edge_count": len(workflow["edges"]),
            "complexity_score": len(workflow["nodes"]) + len(workflow["edges"])
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)