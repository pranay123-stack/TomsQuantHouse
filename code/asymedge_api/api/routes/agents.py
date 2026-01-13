"""
ASYMEdge Dashboard API - Agent Management Routes

Agent management endpoints providing:
- Agent definition CRUD operations
- Agent instance lifecycle management
- Agent query processing and history
- Performance monitoring and analytics
- Real-time agent activity updates
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from api.database.models import AgentDefinition, AgentInstance, User
from api.database.database import get_db_session
from api.schemas import (
    AgentDefinitionResponse, AgentDefinitionCreate, AgentDefinitionUpdate,
    AgentInstanceResponse, AgentInstanceCreate, AgentInstanceUpdate,
    AgentQueryResponse, AgentQueryCreate,
    PaginationParams, APIResponse, ErrorResponse
)
from api.services.agent_service import agent_query_service, agent_manager
from api.routes.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Agent Definition Endpoints

@router.get("/definitions", response_model=List[AgentDefinitionResponse])
async def get_agent_definitions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Get all agent definitions with optional filtering"""
    try:
        with get_db_session() as db:
            query = db.query(AgentDefinition)
            
            # Filter by active status if specified
            if is_active is not None:
                query = query.filter(AgentDefinition.is_active == is_active)
            
            # Apply pagination
            definitions = query.offset(skip).limit(limit).all()
            
            return [
                AgentDefinitionResponse(
                    id=definition.id,
                    name=definition.name,
                    description=definition.description,
                    letta_agent_type=definition.letta_agent_type,
                    configuration=definition.configuration,
                    input_schema=definition.input_schema,
                    output_schema=definition.output_schema,
                    version=definition.version,
                    is_active=definition.is_active,
                    created_by=definition.created_by,
                    created_at=definition.created_at,
                    updated_at=definition.updated_at
                )
                for definition in definitions
            ]
            
    except Exception as e:
        logger.error(f"Failed to get agent definitions: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/definitions/{definition_id}", response_model=AgentDefinitionResponse)
async def get_agent_definition(
    definition_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get a specific agent definition by ID"""
    try:
        with get_db_session() as db:
            definition = db.query(AgentDefinition).filter(
                AgentDefinition.id == definition_id
            ).first()
            
            if not definition:
                raise HTTPException(status_code=404, detail={"error": "Agent definition not found"})
            
            return AgentDefinitionResponse(
                id=definition.id,
                name=definition.name,
                description=definition.description,
                letta_agent_type=definition.letta_agent_type,
                configuration=definition.configuration,
                input_schema=definition.input_schema,
                output_schema=definition.output_schema,
                version=definition.version,
                is_active=definition.is_active,
                created_by=definition.created_by,
                created_at=definition.created_at,
                updated_at=definition.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent definition {definition_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/definitions", response_model=AgentDefinitionResponse)
async def create_agent_definition(
    definition_data: AgentDefinitionCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new agent definition"""
    try:
        with get_db_session() as db:
            # Create new definition
            definition = AgentDefinition(
                name=definition_data.name,
                description=definition_data.description,
                letta_agent_type=definition_data.letta_agent_type,
                configuration=definition_data.configuration,
                input_schema=definition_data.input_schema,
                output_schema=definition_data.output_schema,
                version=definition_data.version,
                created_by=current_user.id
            )
            
            db.add(definition)
            db.commit()
            db.refresh(definition)
            
            return AgentDefinitionResponse(
                id=definition.id,
                name=definition.name,
                description=definition.description,
                letta_agent_type=definition.letta_agent_type,
                configuration=definition.configuration,
                input_schema=definition.input_schema,
                output_schema=definition.output_schema,
                version=definition.version,
                is_active=definition.is_active,
                created_by=definition.created_by,
                created_at=definition.created_at,
                updated_at=definition.updated_at
            )
            
    except Exception as e:
        logger.error(f"Failed to create agent definition: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.put("/definitions/{definition_id}", response_model=AgentDefinitionResponse)
async def update_agent_definition(
    definition_id: int,
    definition_data: AgentDefinitionUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an existing agent definition"""
    try:
        with get_db_session() as db:
            definition = db.query(AgentDefinition).filter(
                AgentDefinition.id == definition_id
            ).first()
            
            if not definition:
                raise HTTPException(status_code=404, detail={"error": "Agent definition not found"})
            
            # Update fields
            update_data = definition_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(definition, field, value)
            
            definition.updated_at = datetime.now()
            
            db.commit()
            db.refresh(definition)
            
            return AgentDefinitionResponse(
                id=definition.id,
                name=definition.name,
                description=definition.description,
                letta_agent_type=definition.letta_agent_type,
                configuration=definition.configuration,
                input_schema=definition.input_schema,
                output_schema=definition.output_schema,
                version=definition.version,
                is_active=definition.is_active,
                created_by=definition.created_by,
                created_at=definition.created_at,
                updated_at=definition.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent definition {definition_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/definitions/{definition_id}", response_model=APIResponse)
async def delete_agent_definition(
    definition_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete an agent definition (soft delete by setting is_active to False)"""
    try:
        with get_db_session() as db:
            definition = db.query(AgentDefinition).filter(
                AgentDefinition.id == definition_id
            ).first()
            
            if not definition:
                raise HTTPException(status_code=404, detail={"error": "Agent definition not found"})
            
            # Soft delete
            definition.is_active = False
            definition.updated_at = datetime.now()
            
            db.commit()
            
            return APIResponse(
                success=True,
                message="Agent definition deleted successfully",
                data={"definition_id": definition_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent definition {definition_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Agent Instance Endpoints

@router.get("/instances", response_model=List[AgentInstanceResponse])
async def get_agent_instances(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    definition_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Get agent instances with optional filtering"""
    try:
        with get_db_session() as db:
            query = db.query(AgentInstance).filter(
                AgentInstance.owner_id == current_user.id
            )
            
            # Apply filters
            if status:
                query = query.filter(AgentInstance.status == status)
            if definition_id:
                query = query.filter(AgentInstance.agent_definition_id == definition_id)
            
            # Apply pagination
            instances = query.offset(skip).limit(limit).all()
            
            results = []
            for instance in instances:
                definition = db.query(AgentDefinition).filter(
                    AgentDefinition.id == instance.agent_definition_id
                ).first()
                
                results.append(AgentInstanceResponse(
                    id=instance.id,
                    name=instance.name,
                    agent_definition_id=instance.agent_definition_id,
                    letta_agent_id=instance.letta_agent_id,
                    status=instance.status,
                    configuration=instance.configuration,
                    memory_state=instance.memory_state,
                    last_activity=instance.last_activity,
                    resource_usage=instance.resource_usage,
                    metadata=instance.metadata,
                    created_at=instance.created_at,
                    updated_at=instance.updated_at,
                    definition=AgentDefinitionResponse(
                        id=definition.id,
                        name=definition.name,
                        description=definition.description,
                        letta_agent_type=definition.letta_agent_type,
                        configuration=definition.configuration,
                        input_schema=definition.input_schema,
                        output_schema=definition.output_schema,
                        version=definition.version,
                        is_active=definition.is_active,
                        created_by=definition.created_by,
                        created_at=definition.created_at,
                        updated_at=definition.updated_at
                    )
                ))
            
            return results
            
    except Exception as e:
        logger.error(f"Failed to get agent instances: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/instances/{instance_id}", response_model=AgentInstanceResponse)
async def get_agent_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get a specific agent instance by ID"""
    try:
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
            
            definition = db.query(AgentDefinition).filter(
                AgentDefinition.id == instance.agent_definition_id
            ).first()
            
            return AgentInstanceResponse(
                id=instance.id,
                name=instance.name,
                agent_definition_id=instance.agent_definition_id,
                letta_agent_id=instance.letta_agent_id,
                status=instance.status,
                configuration=instance.configuration,
                memory_state=instance.memory_state,
                last_activity=instance.last_activity,
                resource_usage=instance.resource_usage,
                metadata=instance.metadata,
                created_at=instance.created_at,
                updated_at=instance.updated_at,
                definition=AgentDefinitionResponse(
                    id=definition.id,
                    name=definition.name,
                    description=definition.description,
                    letta_agent_type=definition.letta_agent_type,
                    configuration=definition.configuration,
                    input_schema=definition.input_schema,
                    output_schema=definition.output_schema,
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
        logger.error(f"Failed to get agent instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/instances", response_model=AgentInstanceResponse)
async def create_agent_instance(
    instance_data: AgentInstanceCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Create and start a new agent instance"""
    try:
        with get_db_session() as db:
            # Verify definition exists and is active
            definition = db.query(AgentDefinition).filter(
                AgentDefinition.id == instance_data.agent_definition_id,
                AgentDefinition.is_active == True
            ).first()
            
            if not definition:
                raise HTTPException(status_code=404, detail={"error": "Agent definition not found or inactive"})
            
            # Create Letta agent in background
            async def start_agent():
                try:
                    letta_agent_id = await agent_manager.start_agent_instance(
                        instance_data.agent_definition_id,
                        instance_data.name,
                        instance_data.configuration,
                        current_user.id
                    )
                    
                    # Update instance with Letta agent ID
                    with get_db_session() as session:
                        instance = session.query(AgentInstance).filter(
                            AgentInstance.id == instance.id
                        ).first()
                        if instance:
                            instance.letta_agent_id = letta_agent_id
                            instance.status = "running"
                            session.commit()
                    
                except Exception as e:
                    logger.error(f"Failed to start Letta agent: {e}")
                    with get_db_session() as session:
                        instance = session.query(AgentInstance).filter(
                            AgentInstance.id == instance.id
                        ).first()
                        if instance:
                            instance.status = "error"
                            session.commit()
            
            # Create database record
            instance = AgentInstance(
                name=instance_data.name,
                agent_definition_id=instance_data.agent_definition_id,
                owner_id=current_user.id,
                configuration=instance_data.configuration,
                status="starting"
            )
            
            db.add(instance)
            db.commit()
            db.refresh(instance)
            
            # Start Letta agent in background
            background_tasks.add_task(start_agent)
            
            return AgentInstanceResponse(
                id=instance.id,
                name=instance.name,
                agent_definition_id=instance.agent_definition_id,
                letta_agent_id=instance.letta_agent_id,
                status=instance.status,
                configuration=instance.configuration,
                memory_state=instance.memory_state,
                last_activity=instance.last_activity,
                resource_usage=instance.resource_usage,
                metadata=instance.metadata,
                created_at=instance.created_at,
                updated_at=instance.updated_at,
                definition=AgentDefinitionResponse(
                    id=definition.id,
                    name=definition.name,
                    description=definition.description,
                    letta_agent_type=definition.letta_agent_type,
                    configuration=definition.configuration,
                    input_schema=definition.input_schema,
                    output_schema=definition.output_schema,
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
        logger.error(f"Failed to create agent instance: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.put("/instances/{instance_id}", response_model=AgentInstanceResponse)
async def update_agent_instance(
    instance_id: int,
    instance_data: AgentInstanceUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an agent instance"""
    try:
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
            
            # Update fields
            update_data = instance_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(instance, field, value)
            
            instance.updated_at = datetime.now()
            
            db.commit()
            db.refresh(instance)
            
            definition = db.query(AgentDefinition).filter(
                AgentDefinition.id == instance.agent_definition_id
            ).first()
            
            return AgentInstanceResponse(
                id=instance.id,
                name=instance.name,
                agent_definition_id=instance.agent_definition_id,
                letta_agent_id=instance.letta_agent_id,
                status=instance.status,
                configuration=instance.configuration,
                memory_state=instance.memory_state,
                last_activity=instance.last_activity,
                resource_usage=instance.resource_usage,
                metadata=instance.metadata,
                created_at=instance.created_at,
                updated_at=instance.updated_at,
                definition=AgentDefinitionResponse(
                    id=definition.id,
                    name=definition.name,
                    description=definition.description,
                    letta_agent_type=definition.letta_agent_type,
                    configuration=definition.configuration,
                    input_schema=definition.input_schema,
                    output_schema=definition.output_schema,
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
        logger.error(f"Failed to update agent instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/instances/{instance_id}", response_model=APIResponse)
async def delete_agent_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user)
):
    """Stop and delete an agent instance"""
    try:
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
            
            # Stop Letta agent if running
            if instance.letta_agent_id and instance.status in ["running", "paused"]:
                try:
                    await agent_manager.stop_agent_instance(instance.letta_agent_id)
                except Exception as e:
                    logger.warning(f"Failed to stop Letta agent {instance.letta_agent_id}: {e}")
            
            # Delete instance
            db.delete(instance)
            db.commit()
            
            return APIResponse(
                success=True,
                message="Agent instance deleted successfully",
                data={"instance_id": instance_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/instances/{instance_id}/start", response_model=APIResponse)
async def start_agent_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user)
):
    """Start a stopped agent instance"""
    try:
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
            
            if instance.status in ["running", "starting"]:
                raise HTTPException(status_code=400, detail={"error": "Agent instance is already running"})
            
            # Start Letta agent
            letta_agent_id = await agent_manager.start_agent_instance(
                instance.agent_definition_id,
                instance.name,
                instance.configuration,
                current_user.id
            )
            
            # Update instance
            instance.letta_agent_id = letta_agent_id
            instance.status = "running"
            instance.updated_at = datetime.now()
            
            db.commit()
            
            return APIResponse(
                success=True,
                message="Agent instance started successfully",
                data={"instance_id": instance_id, "letta_agent_id": letta_agent_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start agent instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/instances/{instance_id}/stop", response_model=APIResponse)
async def stop_agent_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user)
):
    """Stop a running agent instance"""
    try:
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
            
            if instance.status not in ["running", "starting"]:
                raise HTTPException(status_code=400, detail={"error": "Agent instance is not running"})
            
            # Stop Letta agent
            if instance.letta_agent_id:
                success = await agent_manager.stop_agent_instance(instance.letta_agent_id)
                if not success:
                    logger.warning(f"Failed to stop Letta agent {instance.letta_agent_id}")
            
            # Update instance status
            instance.status = "stopped"
            instance.updated_at = datetime.now()
            
            db.commit()
            
            return APIResponse(
                success=True,
                message="Agent instance stopped successfully",
                data={"instance_id": instance_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop agent instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Agent Query Endpoints

@router.post("/instances/{instance_id}/query", response_model=AgentQueryResponse)
async def query_agent(
    instance_id: int,
    query_data: AgentQueryCreate,
    current_user: User = Depends(get_current_user)
):
    """Send a query to an agent instance"""
    try:
        # Verify agent instance ownership
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
            
            if instance.status != "running":
                raise HTTPException(status_code=400, detail={"error": "Agent instance is not running"})
        
        # Process query
        query_data.agent_instance_id = instance_id
        response = await agent_query_service.execute_query(instance_id, query_data)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query agent instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/instances/{instance_id}/queries", response_model=List[AgentQueryResponse])
async def get_agent_queries(
    instance_id: int,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get query history for an agent instance"""
    try:
        # Verify agent instance ownership
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
        
        # Get query history
        queries = await agent_query_service.get_query_history(instance_id, limit)
        
        return queries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent queries for instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/instances/{instance_id}/metrics", response_model=Dict[str, Any])
async def get_agent_metrics(
    instance_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for an agent instance"""
    try:
        # Verify agent instance ownership
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
        
        # Get metrics
        metrics = await agent_query_service.get_agent_performance_metrics(instance_id)
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent metrics for instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/instances/{instance_id}/status", response_model=Dict[str, Any])
async def get_agent_status(
    instance_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get current status of an agent instance"""
    try:
        # Verify agent instance ownership
        with get_db_session() as db:
            instance = db.query(AgentInstance).filter(
                AgentInstance.id == instance_id,
                AgentInstance.owner_id == current_user.id
            ).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail={"error": "Agent instance not found"})
        
        # Get Letta agent status
        if instance.letta_agent_id:
            status = await agent_manager.get_agent_status(instance.letta_agent_id)
        else:
            status = {"status": "no_letta_agent", "message": "No Letta agent ID configured"}
        
        return {
            "instance_id": instance_id,
            "database_status": instance.status,
            "letta_status": status,
            "last_activity": instance.last_activity.isoformat() if instance.last_activity else None,
            "updated_at": instance.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent status for instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})