"""
Workflow service for business logic
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import uuid4

from ..auth.auth_models import (
    Workflow, WorkflowCreate, WorkflowUpdate, WorkflowExecutionRequest,
    WorkflowExecutionResponse, BatchWorkflowExecutionRequest, WorkflowStatus
)
from ..core.database import db_manager

logger = logging.getLogger(__name__)

class WorkflowService:
    """Service for workflow operations"""
    
    def __init__(self):
        self.max_concurrent_workflows = 10
        self.active_executions = {}
    
    async def create_workflow(
        self, 
        workflow_data: WorkflowCreate, 
        user_id: str
    ) -> Workflow:
        """Create new workflow"""
        async with db_manager.get_session() as session:
            # Create workflow record
            workflow = Workflow(
                name=workflow_data.name,
                description=workflow_data.description,
                workflow_type=workflow_data.workflow_type,
                config=workflow_data.config,
                timeout_minutes=workflow_data.timeout_minutes,
                priority=workflow_data.priority,
                user_id=user_id,
                status=WorkflowStatus.PENDING
            )
            
            session.add(workflow)
            await session.commit()
            await session.refresh(workflow)
            
            logger.info(f"Created workflow: {workflow.id} for user: {user_id}")
            return workflow
    
    async def get_workflow(
        self, 
        workflow_id: str, 
        user_id: str
    ) -> Optional[Workflow]:
        """Get workflow by ID"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                "SELECT * FROM workflows WHERE id = ? AND user_id = ?",
                (workflow_id, user_id)
            )
            workflow_data = result.fetchone()
            
            if workflow_data:
                return self._row_to_workflow(workflow_data)
            return None
    
    async def list_workflows(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        workflow_type: Optional[str] = None
    ) -> Tuple[List[Workflow], int]:
        """List workflows with pagination and filtering"""
        async with db_manager.get_session() as session:
            # Build query
            where_conditions = ["user_id = ?"]
            params = [user_id]
            
            if status:
                where_conditions.append("status = ?")
                params.append(status)
            
            if workflow_type:
                where_conditions.append("workflow_type = ?")
                params.append(workflow_type)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM workflows WHERE {where_clause}"
            result = await session.execute(count_query, params)
            total = result.fetchone()[0]
            
            # Get workflows with pagination
            offset = (page - 1) * per_page
            query = f"""
                SELECT * FROM workflows 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([per_page, offset])
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            workflows = [self._row_to_workflow(row) for row in rows]
            return workflows, total
    
    async def update_workflow(
        self,
        workflow_id: str,
        workflow_data: WorkflowUpdate,
        user_id: str
    ) -> Optional[Workflow]:
        """Update workflow"""
        async with db_manager.get_session() as session:
            # Get existing workflow
            result = await session.execute(
                "SELECT * FROM workflows WHERE id = ? AND user_id = ?",
                (workflow_id, user_id)
            )
            existing = result.fetchone()
            
            if not existing:
                return None
            
            # Build update query
            update_fields = []
            params = []
            
            if workflow_data.name is not None:
                update_fields.append("name = ?")
                params.append(workflow_data.name)
            
            if workflow_data.description is not None:
                update_fields.append("description = ?")
                params.append(workflow_data.description)
            
            if workflow_data.config is not None:
                update_fields.append("config = ?")
                params.append(str(workflow_data.config))
            
            if workflow_data.timeout_minutes is not None:
                update_fields.append("timeout_minutes = ?")
                params.append(workflow_data.timeout_minutes)
            
            if workflow_data.priority is not None:
                update_fields.append("priority = ?")
                params.append(workflow_data.priority)
            
            if update_fields:
                update_fields.append("updated_at = ?")
                params.append(datetime.now())
                params.extend([workflow_id, user_id])
                
                query = f"UPDATE workflows SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
                await session.execute(query, params)
                await session.commit()
            
            return await self.get_workflow(workflow_id, user_id)
    
    async def delete_workflow(self, workflow_id: str, user_id: str) -> bool:
        """Delete workflow"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                "DELETE FROM workflows WHERE id = ? AND user_id = ?",
                (workflow_id, user_id)
            )
            await session.commit()
            
            return result.rowcount > 0
    
    async def execute_workflow(
        self,
        workflow_id: str,
        execution_request: WorkflowExecutionRequest,
        user_id: str
    ) -> WorkflowExecutionResponse:
        """Execute workflow"""
        # Verify workflow exists and belongs to user
        workflow = await self.get_workflow(workflow_id, user_id)
        if not workflow:
            raise ValueError("Workflow not found")
        
        # Create execution record
        execution_id = str(uuid4())
        
        # Update workflow status
        async with db_manager.get_session() as session:
            await session.execute(
                "UPDATE workflows SET status = ?, updated_at = ? WHERE id = ?",
                (WorkflowStatus.RUNNING, datetime.now(), workflow_id)
            )
            await session.commit()
        
        # Execute workflow (simulate async execution)
        execution_response = WorkflowExecutionResponse(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING
        )
        
        # Store execution for tracking
        self.active_executions[execution_id] = {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "started_at": datetime.now(),
            "status": WorkflowStatus.RUNNING
        }
        
        # If synchronous, wait for completion
        if execution_request.synchronous:
            try:
                result = await self._execute_workflow_sync(workflow, execution_request, execution_id)
                execution_response.status = WorkflowStatus.COMPLETED
                execution_response.result = result
                
                # Update workflow status
                async with db_manager.get_session() as session:
                    await session.execute(
                        "UPDATE workflows SET status = ?, updated_at = ? WHERE id = ?",
                        (WorkflowStatus.COMPLETED, datetime.now(), workflow_id)
                    )
                    await session.commit()
            except Exception as e:
                execution_response.status = WorkflowStatus.FAILED
                logger.error(f"Workflow execution failed: {e}")
        
        return execution_response
    
    async def execute_batch_workflows(
        self,
        batch_request: BatchWorkflowExecutionRequest,
        user_id: str
    ) -> List[WorkflowExecutionResponse]:
        """Execute multiple workflows in batch"""
        responses = []
        
        # Process in batches
        semaphore = asyncio.Semaphore(batch_request.max_concurrent)
        
        async def execute_with_semaphore(execution_request: WorkflowExecutionRequest):
            async with semaphore:
                return await self.execute_workflow(
                    execution_request.workflow_id,
                    execution_request,
                    user_id
                )
        
        # Execute all workflows
        tasks = [
            execute_with_semaphore(exec_req)
            for exec_req in batch_request.executions
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                responses[i] = WorkflowExecutionResponse(
                    execution_id=str(uuid4()),
                    workflow_id=batch_request.executions[i].workflow_id,
                    status=WorkflowStatus.FAILED,
                    message=str(response)
                )
        
        return responses
    
    async def cancel_workflow(
        self,
        workflow_id: str,
        execution_id: Optional[str],
        user_id: str
    ) -> bool:
        """Cancel workflow execution"""
        async with db_manager.get_session() as session:
            # Update workflow status
            result = await session.execute(
                "UPDATE workflows SET status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (WorkflowStatus.CANCELLED, datetime.now(), workflow_id, user_id)
            )
            await session.commit()
            
            if result.rowcount == 0:
                return False
            
            # Cancel active execution if specified
            if execution_id and execution_id in self.active_executions:
                self.active_executions[execution_id]["status"] = WorkflowStatus.CANCELLED
            
            return True
    
    async def get_workflow_status(
        self,
        workflow_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get workflow current status"""
        workflow = await self.get_workflow(workflow_id, user_id)
        if not workflow:
            return None
        
        # Get recent execution info
        async with db_manager.get_session() as session:
            result = await session.execute(
                "SELECT * FROM workflow_executions WHERE workflow_id = ? ORDER BY started_at DESC LIMIT 1",
                (workflow_id,)
            )
            execution = result.fetchone()
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.status,
            "name": workflow.name,
            "workflow_type": workflow.workflow_type,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "last_execution": execution[1:] if execution else None
        }
    
    async def get_workflow_history(
        self,
        workflow_id: str,
        user_id: str,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get workflow execution history"""
        async with db_manager.get_session() as session:
            # Get total count
            count_result = await session.execute(
                "SELECT COUNT(*) FROM workflow_executions WHERE workflow_id = ?",
                (workflow_id,)
            )
            total = count_result.fetchone()[0]
            
            # Get executions
            offset = (page - 1) * per_page
            result = await session.execute(
                """
                SELECT * FROM workflow_executions 
                WHERE workflow_id = ?
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,
                (workflow_id, per_page, offset)
            )
            rows = result.fetchall()
            
            history = []
            for row in rows:
                history.append({
                    "execution_id": row[0],
                    "workflow_id": row[1],
                    "status": row[2],
                    "started_at": row[3],
                    "completed_at": row[4],
                    "result": row[5],
                    "error_message": row[6]
                })
            
            return history, total
    
    async def clone_workflow(
        self,
        workflow_id: str,
        new_name: Optional[str],
        user_id: str
    ) -> Optional[Workflow]:
        """Clone existing workflow"""
        original = await self.get_workflow(workflow_id, user_id)
        if not original:
            return None
        
        clone_data = WorkflowCreate(
            name=new_name or f"{original.name} (Copy)",
            description=original.description,
            workflow_type=original.workflow_type,
            config=original.config,
            timeout_minutes=original.timeout_minutes,
            priority=original.priority
        )
        
        return await self.create_workflow(clone_data, user_id)
    
    async def get_workflow_metrics(
        self,
        workflow_id: str,
        user_id: str,
        time_range_hours: int
    ) -> Optional[Dict[str, Any]]:
        """Get workflow execution metrics"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        async with db_manager.get_session() as session:
            # Get workflow executions in time range
            result = await session.execute(
                """
                SELECT status, COUNT(*) as count, AVG(
                    CASE 
                        WHEN completed_at IS NOT NULL AND started_at IS NOT NULL 
                        THEN JULIANDAY(completed_at) - JULIANDAY(started_at)
                        ELSE NULL
                    END
                ) as avg_duration
                FROM workflow_executions 
                WHERE workflow_id = ? AND started_at >= ?
                GROUP BY status
                """,
                (workflow_id, cutoff_time.isoformat())
            )
            rows = result.fetchall()
            
            if not rows:
                return None
            
            # Calculate metrics
            total_executions = sum(row[1] for row in rows)
            completed_executions = sum(row[1] for row in rows if row[0] == WorkflowStatus.COMPLETED)
            failed_executions = sum(row[1] for row in rows if row[0] == WorkflowStatus.FAILED)
            
            avg_duration = None
            for row in rows:
                if row[2] is not None:
                    avg_duration = row[2] * 24 * 3600  # Convert days to seconds
                    break
            
            return {
                "workflow_id": workflow_id,
                "time_range_hours": time_range_hours,
                "total_executions": total_executions,
                "completed_executions": completed_executions,
                "failed_executions": failed_executions,
                "success_rate": completed_executions / total_executions if total_executions > 0 else 0,
                "failure_rate": failed_executions / total_executions if total_executions > 0 else 0,
                "avg_execution_time_seconds": avg_duration,
                "status_breakdown": {row[0]: row[1] for row in rows}
            }
    
    async def validate_workflow_config(
        self,
        workflow_data: WorkflowCreate
    ) -> Dict[str, Any]:
        """Validate workflow configuration"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Basic validation
        if not workflow_data.name or len(workflow_data.name.strip()) == 0:
            validation_result["errors"].append("Workflow name is required")
            validation_result["valid"] = False
        
        if not workflow_data.workflow_type:
            validation_result["errors"].append("Workflow type is required")
            validation_result["valid"] = False
        
        # Config validation
        if not isinstance(workflow_data.config, dict):
            validation_result["errors"].append("Config must be a dictionary")
            validation_result["valid"] = False
        
        # Timeout validation
        if workflow_data.timeout_minutes <= 0:
            validation_result["errors"].append("Timeout must be positive")
            validation_result["valid"] = False
        
        return validation_result
    
    async def _execute_workflow_sync(
        self,
        workflow: Workflow,
        execution_request: WorkflowExecutionRequest,
        execution_id: str
    ) -> Dict[str, Any]:
        """Execute workflow synchronously (simulated)"""
        # Simulate workflow execution
        await asyncio.sleep(2)  # Simulate processing time
        
        # Create execution record
        async with db_manager.get_session() as session:
            await session.execute(
                """
                INSERT INTO workflow_executions 
                (id, workflow_id, status, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    workflow.id,
                    WorkflowStatus.COMPLETED,
                    datetime.now(),
                    datetime.now()
                )
            )
            await session.commit()
        
        # Simulate result
        return {
            "execution_id": execution_id,
            "status": "completed",
            "result": {"output": "Workflow execution completed successfully"},
            "execution_time": 2.0
        }
    
    def _row_to_workflow(self, row) -> Workflow:
        """Convert database row to Workflow model"""
        return Workflow(
            id=row[0],
            name=row[1],
            description=row[2],
            workflow_type=row[3],
            config=eval(row[4]) if row[4] else {},
            timeout_minutes=row[5],
            priority=row[6],
            user_id=row[7],
            status=WorkflowStatus(row[8]),
            created_at=row[9],
            updated_at=row[10],
            started_at=row[11],
            completed_at=row[12],
            error_message=row[13],
            result=row[14],
            execution_count=row[15]
        )