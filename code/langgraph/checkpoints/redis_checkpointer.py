"""
Redis Checkpointer for LangGraph
Provides persistent state management and checkpointing for workflow execution
"""

import json
import pickle
import uuid
import time
from typing import Any, Dict, List, Optional, TypeVar, Union
from datetime import datetime, timedelta
import logging
from dataclasses import asdict

from ..workflows.state import WorkflowState, WorkflowStatus, NodeResult

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RedisCheckpointer:
    """Redis-based checkpointer for LangGraph workflow state management"""
    
    def __init__(self, redis_client, checkpoint_ttl: int = 86400):
        """
        Initialize Redis checkpointer
        
        Args:
            redis_client: Redis client instance
            checkpoint_ttl: Time to live for checkpoint data in seconds (default 24h)
        """
        self.redis_client = redis_client
        self.checkpoint_ttl = checkpoint_ttl
        self.db = 2  # Use graph state database from existing Redis setup
        
        logger.info(f"RedisCheckpointer initialized with TTL: {checkpoint_ttl}s")
    
    def create_checkpoint(
        self, 
        workflow_id: str, 
        state: WorkflowState, 
        node_name: str,
        save_state_history: bool = True
    ) -> str:
        """
        Create a checkpoint of the current workflow state
        
        Args:
            workflow_id: Unique identifier for the workflow
            state: Current workflow state
            node_name: Name of the current node being executed
            save_state_history: Whether to save the full state history
            
        Returns:
            str: Checkpoint identifier
        """
        try:
            checkpoint_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Prepare checkpoint data
            checkpoint_data = {
                "checkpoint_id": checkpoint_id,
                "workflow_id": workflow_id,
                "node_name": node_name,
                "timestamp": timestamp.isoformat(),
                "state": asdict(state) if hasattr(state, '__dict__') else state,
                "status": state.status.value if hasattr(state.status, 'value') else state.status,
                "current_node": state.current_node,
                "workflow_metadata": {
                    "created_at": timestamp.isoformat(),
                    "ttl": self.checkpoint_ttl,
                    "version": "1.0"
                }
            }
            
            # Add to history if requested
            if save_state_history:
                history_entry = {
                    "checkpoint_id": checkpoint_id,
                    "node_name": node_name,
                    "timestamp": timestamp.isoformat(),
                    "status": checkpoint_data["status"]
                }
                
                # Store in workflow history
                self._store_workflow_history(workflow_id, history_entry)
            
            # Serialize and store checkpoint
            self._store_checkpoint_data(checkpoint_id, checkpoint_data)
            
            # Update workflow state with checkpoint info
            state.checkpoint_id = checkpoint_id
            state.last_checkpoint_time = timestamp
            
            logger.info(f"Created checkpoint {checkpoint_id} for workflow {workflow_id}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint for workflow {workflow_id}: {e}")
            raise
    
    def restore_checkpoint(
        self, 
        checkpoint_id: str
    ) -> Optional[WorkflowState]:
        """
        Restore workflow state from a checkpoint
        
        Args:
            checkpoint_id: Unique identifier for the checkpoint
            
        Returns:
            WorkflowState: Restored workflow state or None if not found
        """
        try:
            checkpoint_data = self._get_checkpoint_data(checkpoint_id)
            if not checkpoint_data:
                logger.warning(f"Checkpoint {checkpoint_id} not found")
                return None
            
            # Restore state from checkpoint data
            state_dict = checkpoint_data["state"]
            
            # Convert back to WorkflowState object
            state = self._dict_to_workflow_state(state_dict)
            state.checkpoint_id = checkpoint_id
            state.last_checkpoint_time = datetime.fromisoformat(checkpoint_data["timestamp"])
            
            logger.info(f"Restored checkpoint {checkpoint_id} for workflow {state_dict.get('workflow_id', 'unknown')}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            return None
    
    def save_node_result(
        self, 
        workflow_id: str, 
        node_name: str, 
        result: NodeResult,
        checkpoint_id: Optional[str] = None
    ) -> bool:
        """
        Save the result of a node execution
        
        Args:
            workflow_id: Unique identifier for the workflow
            node_name: Name of the executed node
            result: Node execution result
            checkpoint_id: Optional checkpoint ID to associate with
            
        Returns:
            bool: Success status
        """
        try:
            result_key = f"node_result:{workflow_id}:{node_name}:{result.timestamp.isoformat()}"
            
            result_data = {
                "result": result.to_dict(),
                "checkpoint_id": checkpoint_id,
                "workflow_id": workflow_id,
                "node_name": node_name,
                "saved_at": datetime.now().isoformat()
            }
            
            serialized_result = pickle.dumps(result_data)
            
            self.redis_client.select(self.db)
            self.redis_client.setex(result_key, self.checkpoint_ttl, serialized_result)
            
            logger.info(f"Saved node result for {node_name} in workflow {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save node result for {node_name}: {e}")
            return False
    
    def get_node_results(
        self, 
        workflow_id: str, 
        node_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all node results for a workflow
        
        Args:
            workflow_id: Unique identifier for the workflow
            node_name: Optional node name filter
            
        Returns:
            List of node results
        """
        try:
            self.redis_client.select(self.db)
            
            # Pattern for node results
            pattern = f"node_result:{workflow_id}:*"
            if node_name:
                pattern = f"node_result:{workflow_id}:{node_name}:*"
            
            keys = self.redis_client.keys(pattern)
            results = []
            
            for key in keys:
                try:
                    serialized_result = self.redis_client.get(key)
                    if serialized_result:
                        result_data = pickle.loads(serialized_result)
                        results.append(result_data["result"])
                except Exception as e:
                    logger.warning(f"Failed to load result from key {key}: {e}")
                    continue
            
            # Sort by timestamp
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Failed to get node results for workflow {workflow_id}: {e}")
            return []
    
    def get_workflow_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get the complete execution history for a workflow
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            List of execution history entries
        """
        try:
            self.redis_client.select(self.db)
            
            history_key = f"workflow_history:{workflow_id}"
            history_data = self.redis_client.get(history_key)
            
            if history_data:
                return pickle.loads(history_data)
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get workflow history for {workflow_id}: {e}")
            return []
    
    def list_workflows(
        self, 
        status_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all workflows with optional status filtering
        
        Args:
            status_filter: Optional status filter (pending, running, completed, etc.)
            limit: Maximum number of workflows to return
            
        Returns:
            List of workflow metadata
        """
        try:
            self.redis_client.select(self.db)
            
            # Get all checkpoints
            pattern = "checkpoint:*"
            keys = self.redis_client.keys(pattern)
            
            workflows = []
            for key in keys:
                try:
                    checkpoint_data = self._get_checkpoint_data(key.decode().split(":")[-1])
                    if checkpoint_data:
                        metadata = {
                            "workflow_id": checkpoint_data["workflow_id"],
                            "checkpoint_id": checkpoint_data["checkpoint_id"],
                            "status": checkpoint_data["status"],
                            "current_node": checkpoint_data["current_node"],
                            "timestamp": checkpoint_data["timestamp"],
                            "node_name": checkpoint_data["node_name"]
                        }
                        
                        # Apply status filter if provided
                        if not status_filter or metadata["status"] == status_filter:
                            workflows.append(metadata)
                            
                except Exception as e:
                    logger.warning(f"Failed to process checkpoint key {key}: {e}")
                    continue
            
            # Sort by timestamp (most recent first)
            workflows.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Apply limit
            return workflows[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete all data associated with a workflow
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            bool: Success status
        """
        try:
            self.redis_client.select(self.db)
            
            # Delete checkpoints
            checkpoint_pattern = f"checkpoint:{workflow_id}:*"
            checkpoint_keys = self.redis_client.keys(checkpoint_pattern)
            for key in checkpoint_keys:
                self.redis_client.delete(key)
            
            # Delete node results
            result_pattern = f"node_result:{workflow_id}:*"
            result_keys = self.redis_client.keys(result_pattern)
            for key in result_keys:
                self.redis_client.delete(key)
            
            # Delete workflow history
            history_key = f"workflow_history:{workflow_id}"
            self.redis_client.delete(history_key)
            
            logger.info(f"Deleted workflow {workflow_id} and all associated data")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False
    
    def cleanup_expired_checkpoints(self) -> int:
        """
        Clean up expired checkpoints
        
        Returns:
            int: Number of expired checkpoints cleaned up
        """
        try:
            # Redis TTL will automatically handle cleanup
            # This method is for manual cleanup and reporting
            self.redis_client.select(self.db)
            
            all_keys = self.redis_client.keys("checkpoint:*")
            total_keys = len(all_keys)
            
            cleaned_count = 0
            for key in all_keys:
                try:
                    ttl = self.redis_client.ttl(key)
                    if ttl == -1:  # Key has no expiry
                        # Set expiry based on workflow status
                        checkpoint_data = self._get_checkpoint_data(key.decode().split(":")[-1])
                        if checkpoint_data and checkpoint_data.get("status") in ["completed", "failed", "cancelled"]:
                            self.redis_client.expire(key, self.checkpoint_ttl)
                except Exception:
                    continue
            
            logger.info(f"Cleanup completed. Processed {total_keys} checkpoints")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired checkpoints: {e}")
            return 0
    
    def _store_checkpoint_data(self, checkpoint_id: str, data: Dict[str, Any]) -> None:
        """Store checkpoint data in Redis"""
        try:
            self.redis_client.select(self.db)
            
            key = f"checkpoint:{data['workflow_id']}:{checkpoint_id}"
            serialized_data = pickle.dumps(data)
            
            self.redis_client.setex(key, self.checkpoint_ttl, serialized_data)
            
        except Exception as e:
            logger.error(f"Failed to store checkpoint data {checkpoint_id}: {e}")
            raise
    
    def _get_checkpoint_data(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve checkpoint data from Redis"""
        try:
            self.redis_client.select(self.db)
            
            # Find checkpoint by ID across all workflows
            pattern = f"checkpoint:*:{checkpoint_id}"
            keys = self.redis_client.keys(pattern)
            
            if not keys:
                return None
            
            # Get the first matching key
            key = keys[0]
            serialized_data = self.redis_client.get(key)
            
            if serialized_data:
                return pickle.loads(serialized_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get checkpoint data {checkpoint_id}: {e}")
            return None
    
    def _store_workflow_history(self, workflow_id: str, history_entry: Dict[str, Any]) -> None:
        """Store workflow execution history"""
        try:
            self.redis_client.select(self.db)
            
            history_key = f"workflow_history:{workflow_id}"
            existing_history = self.redis_client.get(history_key)
            
            if existing_history:
                history_list = pickle.loads(existing_history)
            else:
                history_list = []
            
            # Add new entry
            history_list.append(history_entry)
            
            # Keep only last 100 entries
            if len(history_list) > 100:
                history_list = history_list[-100:]
            
            serialized_history = pickle.dumps(history_list)
            self.redis_client.setex(history_key, self.checkpoint_ttl, serialized_history)
            
        except Exception as e:
            logger.error(f"Failed to store workflow history for {workflow_id}: {e}")
    
    def _dict_to_workflow_state(self, state_dict: Dict[str, Any]) -> WorkflowState:
        """Convert dictionary back to WorkflowState object"""
        try:
            # Handle nested objects
            if "market_data" in state_dict and state_dict["market_data"]:
                from ..workflows.state import MarketData
                market_data_dict = state_dict["market_data"]
                market_data_dict["timestamp"] = datetime.fromisoformat(market_data_dict["timestamp"])
                state_dict["market_data"] = MarketData(**market_data_dict)
            
            if "ml_prediction" in state_dict and state_dict["ml_prediction"]:
                from ..workflows.state import MLPrediction, MLFeatures, DecisionOutcome
                ml_dict = state_dict["ml_prediction"]
                ml_dict["timestamp"] = datetime.fromisoformat(ml_dict["timestamp"])
                ml_dict["decision"] = DecisionOutcome(ml_dict["decision"])
                if "features_used" in ml_dict and ml_dict["features_used"]:
                    ml_dict["features_used"] = MLFeatures(**ml_dict["features_used"])
                state_dict["ml_prediction"] = MLPrediction(**ml_dict)
            
            if "risk_assessment" in state_dict and state_dict["risk_assessment"]:
                from ..workflows.state import RiskAssessment, RiskLevel
                risk_dict = state_dict["risk_assessment"]
                risk_dict["risk_level"] = RiskLevel(risk_dict["risk_level"])
                state_dict["risk_assessment"] = RiskAssessment(**risk_dict)
            
            if "execution_order" in state_dict and state_dict["execution_order"]:
                from ..workflows.state import ExecutionOrder
                exec_dict = state_dict["execution_order"]
                exec_dict["timestamp"] = datetime.fromisoformat(exec_dict["timestamp"])
                state_dict["execution_order"] = ExecutionOrder(**exec_dict)
            
            # Handle datetime objects
            if "start_time" in state_dict and state_dict["start_time"]:
                state_dict["start_time"] = datetime.fromisoformat(state_dict["start_time"])
            
            if "end_time" in state_dict and state_dict["end_time"]:
                state_dict["end_time"] = datetime.fromisoformat(state_dict["end_time"])
            
            if "last_checkpoint_time" in state_dict and state_dict["last_checkpoint_time"]:
                state_dict["last_checkpoint_time"] = datetime.fromisoformat(state_dict["last_checkpoint_time"])
            
            # Handle enums
            from ..workflows.state import WorkflowStatus
            if "status" in state_dict:
                state_dict["status"] = WorkflowStatus(state_dict["status"])
            
            return WorkflowState(**state_dict)
            
        except Exception as e:
            logger.error(f"Failed to convert dict to WorkflowState: {e}")
            raise