"""
State service for workflow state management
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from uuid import uuid4

from ..auth.auth_models import State, StateCreate, StateUpdate, NodeStatus
from ..core.database import db_manager

logger = logging.getLogger(__name__)

class StateService:
    """Service for workflow state operations"""
    
    async def create_state(self, state_data: StateCreate) -> State:
        """Create workflow state"""
        async with db_manager.get_session() as session:
            state = State(
                workflow_id=state_data.workflow_id,
                node_name=state_data.node_name,
                state_data=state_data.state_data,
                metadata=state_data.metadata,
                status=NodeStatus.PENDING
            )
            
            session.add(state)
            await session.commit()
            await session.refresh(state)
            
            logger.info(f"Created state: {state.id} for workflow: {state.workflow_id}")
            return state
    
    async def get_state(self, state_id: str, user_id: str) -> Optional[State]:
        """Get state by ID"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                SELECT s.* FROM states s 
                JOIN workflows w ON s.workflow_id = w.id 
                WHERE s.id = ? AND w.user_id = ?
                """,
                (state_id, user_id)
            )
            row = result.fetchone()
            
            if row:
                return self._row_to_state(row)
            return None
    
    async def list_states(
        self,
        user_id: str,
        workflow_id: Optional[str] = None,
        node_name: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Tuple[List[State], int]:
        """List states with filtering"""
        async with db_manager.get_session() as session:
            # Build query
            where_conditions = ["w.user_id = ?"]
            params = [user_id]
            
            if workflow_id:
                where_conditions.append("s.workflow_id = ?")
                params.append(workflow_id)
            
            if node_name:
                where_conditions.append("s.node_name = ?")
                params.append(node_name)
            
            if status:
                where_conditions.append("s.status = ?")
                params.append(status)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM states s JOIN workflows w ON s.workflow_id = w.id WHERE {where_clause}"
            result = await session.execute(count_query, params)
            total = result.fetchone()[0]
            
            # Get states with pagination
            offset = (page - 1) * per_page
            query = f"""
                SELECT s.* FROM states s 
                JOIN workflows w ON s.workflow_id = w.id 
                WHERE {where_clause}
                ORDER BY s.created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([per_page, offset])
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            states = [self._row_to_state(row) for row in rows]
            return states, total
    
    async def get_workflow_states(
        self,
        workflow_id: str,
        user_id: str,
        node_name: Optional[str] = None,
        latest_only: bool = False
    ) -> List[State]:
        """Get all states for a workflow"""
        async with db_manager.get_session() as session:
            where_conditions = ["w.user_id = ?", "s.workflow_id = ?"]
            params = [user_id, workflow_id]
            
            if node_name:
                where_conditions.append("s.node_name = ?")
                params.append(node_name)
            
            if latest_only:
                # Get latest state per node
                query = f"""
                    SELECT DISTINCT s.* FROM states s 
                    JOIN workflows w ON s.workflow_id = w.id 
                    WHERE {' AND '.join(where_conditions)}
                    AND s.id IN (
                        SELECT MAX(id) FROM states 
                        WHERE workflow_id = ? {'AND node_name = ?' if node_name else ''}
                        GROUP BY node_name
                    )
                    ORDER BY s.node_name, s.created_at DESC
                """
            else:
                query = f"""
                    SELECT s.* FROM states s 
                    JOIN workflows w ON s.workflow_id = w.id 
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY s.created_at DESC
                """
            
            if latest_only and node_name:
                params.append(workflow_id)
                params.append(node_name)
            elif latest_only:
                params.append(workflow_id)
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            return [self._row_to_state(row) for row in rows]
    
    async def update_state(
        self,
        state_id: str,
        state_data: StateUpdate,
        user_id: str
    ) -> Optional[State]:
        """Update workflow state"""
        async with db_manager.get_session() as session:
            # Verify state belongs to user
            result = await session.execute(
                """
                SELECT s.* FROM states s 
                JOIN workflows w ON s.workflow_id = w.id 
                WHERE s.id = ? AND w.user_id = ?
                """,
                (state_id, user_id)
            )
            existing = result.fetchone()
            
            if not existing:
                return None
            
            # Build update query
            update_fields = []
            params = []
            
            if state_data.state_data is not None:
                update_fields.append("state_data = ?")
                params.append(str(state_data.state_data))
            
            if state_data.metadata is not None:
                update_fields.append("metadata = ?")
                params.append(str(state_data.metadata))
            
            if state_data.status is not None:
                update_fields.append("status = ?")
                params.append(state_data.status.value)
            
            if update_fields:
                update_fields.append("updated_at = ?")
                params.append(datetime.now())
                params.extend([state_id, user_id])
                
                query = f"""
                    UPDATE states s 
                    SET {', '.join(update_fields)}
                    WHERE s.id = ? AND EXISTS (
                        SELECT 1 FROM workflows w WHERE w.id = s.workflow_id AND w.user_id = ?
                    )
                """
                await session.execute(query, params)
                await session.commit()
            
            return await self.get_state(state_id, user_id)
    
    async def delete_state(self, state_id: str, user_id: str) -> bool:
        """Delete workflow state"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                DELETE FROM states 
                WHERE id = ? AND workflow_id IN (
                    SELECT id FROM workflows WHERE user_id = ?
                )
                """,
                (state_id, user_id)
            )
            await session.commit()
            
            return result.rowcount > 0
    
    async def delete_workflow_states(
        self,
        workflow_id: str,
        user_id: str
    ) -> int:
        """Delete all states for a workflow"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                DELETE FROM states 
                WHERE workflow_id = ? AND workflow_id IN (
                    SELECT id FROM workflows WHERE id = ? AND user_id = ?
                )
                """,
                (workflow_id, workflow_id, user_id)
            )
            await session.commit()
            
            return result.rowcount
    
    async def verify_workflow_ownership(
        self,
        workflow_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Verify workflow ownership"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                "SELECT * FROM workflows WHERE id = ? AND user_id = ?",
                (workflow_id, user_id)
            )
            row = result.fetchone()
            
            if row:
                return {"id": row[0], "name": row[1], "user_id": row[7]}
            return None
    
    async def get_state_history(
        self,
        state_id: str,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get state change history"""
        async with db_manager.get_session() as session:
            # Get state and verify ownership
            result = await session.execute(
                """
                SELECT s.* FROM states s 
                JOIN workflows w ON s.workflow_id = w.id 
                WHERE s.id = ? AND w.user_id = ?
                """,
                (state_id, user_id)
            )
            state_row = result.fetchone()
            
            if not state_row:
                return None
            
            # Get state change history (this is a simplified version)
            # In a real implementation, you'd have a state_history table
            return [
                {
                    "state_id": state_row[0],
                    "action": "created",
                    "timestamp": state_row[8],
                    "changes": {"status": "pending"}
                }
            ]
    
    async def create_checkpoint(
        self,
        state_id: str,
        checkpoint_name: Optional[str],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Create checkpoint of current state"""
        state = await self.get_state(state_id, user_id)
        if not state:
            return None
        
        checkpoint_id = str(uuid4())
        
        # In a real implementation, you'd store checkpoints in a separate table
        checkpoint_data = {
            "id": checkpoint_id,
            "name": checkpoint_name or f"Checkpoint {datetime.now().isoformat()}",
            "state_id": state_id,
            "created_at": datetime.now(),
            "state_data": state.state_data,
            "metadata": state.metadata
        }
        
        return checkpoint_data
    
    async def restore_from_checkpoint(
        self,
        checkpoint_id: str,
        workflow_id: Optional[str],
        user_id: str
    ) -> Optional[State]:
        """Restore workflow state from checkpoint"""
        # Simplified checkpoint restoration
        # In a real implementation, you'd retrieve from checkpoint table
        return None
    
    async def compare_states(
        self,
        state_id: str,
        other_state_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Compare two workflow states"""
        state1 = await self.get_state(state_id, user_id)
        state2 = await self.get_state(other_state_id, user_id)
        
        if not state1 or not state2:
            return None
        
        # Simple comparison logic
        differences = {}
        
        if state1.state_data != state2.state_data:
            differences["state_data"] = {
                "state1": state1.state_data,
                "state2": state2.state_data
            }
        
        if state1.status != state2.status:
            differences["status"] = {
                "state1": state1.status,
                "state2": state2.status
            }
        
        return {
            "state1_id": state_id,
            "state2_id": other_state_id,
            "differences": differences,
            "are_identical": len(differences) == 0
        }
    
    async def export_state(
        self,
        state_id: str,
        format: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Export state to file"""
        state = await self.get_state(state_id, user_id)
        if not state:
            return None
        
        export_data = {
            "state": {
                "id": state.id,
                "workflow_id": state.workflow_id,
                "node_name": state.node_name,
                "state_data": state.state_data,
                "metadata": state.metadata,
                "status": state.status,
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat()
            },
            "export_format": format,
            "exported_at": datetime.now().isoformat()
        }
        
        return export_data
    
    async def import_state(
        self,
        workflow_id: str,
        node_name: str,
        state_data: Dict[str, Any],
        import_format: str,
        user_id: str
    ) -> State:
        """Import state from external data"""
        # Verify workflow ownership
        workflow = await self.verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            raise ValueError("Workflow not found or access denied")
        
        state_create = StateCreate(
            workflow_id=workflow_id,
            node_name=node_name,
            state_data=state_data,
            metadata={"imported": True, "format": import_format}
        )
        
        return await self.create_state(state_create)
    
    async def get_latest_states_by_node(
        self,
        workflow_id: str,
        user_id: str
    ) -> List[State]:
        """Get latest state for each node in workflow"""
        return await self.get_workflow_states(
            workflow_id, user_id, latest_only=True
        )
    
    def _row_to_state(self, row) -> State:
        """Convert database row to State model"""
        return State(
            id=row[0],
            workflow_id=row[1],
            node_name=row[2],
            state_data=eval(row[3]) if row[3] else {},
            metadata=eval(row[4]) if row[4] else {},
            created_at=row[5],
            updated_at=row[6],
            status=NodeStatus(row[7]),
            execution_time_ms=row[8]
        )