"""
Trading Workflow Manager
High-level interface for executing trading workflows with Redis checkpointing
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import asdict

from .state_graph import TradingStateGraph
from .state import WorkflowState, WorkflowStatus, DecisionOutcome
from ..checkpoints.redis_checkpointer import RedisCheckpointer

logger = logging.getLogger(__name__)

class TradingWorkflow:
    """
    High-level trading workflow manager
    Provides simplified interface for workflow execution with comprehensive state management
    """
    
    def __init__(
        self,
        redis_checkpointer: RedisCheckpointer,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Trading Workflow Manager
        
        Args:
            redis_checkpointer: Redis-based checkpointing system
            config: Workflow configuration
        """
        self.redis_checkpointer = redis_checkpointer
        self.config = config or self._default_config()
        
        # Initialize StateGraph
        self.state_graph = TradingStateGraph(
            redis_checkpointer=redis_checkpointer,
            market_data_source=self.config.get("market_data_source"),
            ml_model_registry=self.config.get("ml_model_registry"),
            execution_engine=self.config.get("execution_engine"),
            risk_config=self.config.get("risk_config")
        )
        
        # Workflow management
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_callbacks: Dict[str, List[Callable]] = {}
        
        logger.info("TradingWorkflow initialized")
    
    def execute_trading_workflow(
        self,
        symbol: str,
        strategy: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        auto_checkpoint: bool = True,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete trading decision workflow
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            strategy: Trading strategy to use
            metadata: Additional workflow metadata
            auto_checkpoint: Enable automatic checkpointing
            callback_url: URL for workflow completion callback
            
        Returns:
            Dict[str, Any]: Workflow execution result with workflow_id
        """
        try:
            # Generate workflow ID
            workflow_id = f"trading_{symbol}_{strategy}_{int(datetime.now().timestamp())}"
            
            # Prepare metadata
            workflow_metadata = {
                "symbol": symbol,
                "strategy": strategy,
                "executor": "TradingWorkflow",
                "callback_url": callback_url,
                "auto_checkpoint": auto_checkpoint,
                **(metadata or {})
            }
            
            # Register workflow
            self.active_workflows[workflow_id] = {
                "symbol": symbol,
                "strategy": strategy,
                "start_time": datetime.now(),
                "status": "starting",
                "metadata": workflow_metadata
            }
            
            # Execute workflow using StateGraph
            result = self.state_graph.execute_workflow(
                workflow_id=workflow_id,
                symbol=symbol,
                metadata=workflow_metadata,
                checkpoint=auto_checkpoint
            )
            
            # Update workflow status
            self.active_workflows[workflow_id].update({
                "status": result.get("status", "unknown"),
                "end_time": datetime.now(),
                "result": result
            })
            
            # Execute callbacks
            self._execute_workflow_callbacks(workflow_id, result)
            
            logger.info(f"Trading workflow completed: {workflow_id}")
            
            return {
                "workflow_id": workflow_id,
                "status": result.get("status", "unknown"),
                "result": result,
                "execution_time": datetime.now() - self.active_workflows[workflow_id]["start_time"]
            }
            
        except Exception as e:
            logger.error(f"Trading workflow failed: {e}")
            error_result = {
                "workflow_id": workflow_id if 'workflow_id' in locals() else str(uuid.uuid4()),
                "status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            # Execute error callbacks
            if 'workflow_id' in locals() and workflow_id in self.active_workflows:
                self.active_workflows[workflow_id].update({
                    "status": "FAILED",
                    "end_time": datetime.now(),
                    "error": str(e)
                })
                self._execute_workflow_callbacks(workflow_id, error_result)
            
            return error_result
    
    def batch_execute_workflows(
        self,
        workflow_requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple trading workflows concurrently
        
        Args:
            workflow_requests: List of workflow request dictionaries
            max_concurrent: Maximum number of concurrent executions
            
        Returns:
            List[Dict[str, Any]]: Results for each workflow
        """
        try:
            import concurrent.futures
            from threading import Semaphore
            
            # Limit concurrent executions
            semaphore = Semaphore(max_concurrent)
            
            def execute_with_limit(request):
                with semaphore:
                    try:
                        return self.execute_trading_workflow(**request)
                    except Exception as e:
                        logger.error(f"Batch workflow execution failed: {e}")
                        return {
                            "status": "FAILED",
                            "error": str(e),
                            "request": request
                        }
            
            # Execute workflows concurrently
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                future_to_request = {
                    executor.submit(execute_with_limit, request): request 
                    for request in workflow_requests
                }
                
                for future in concurrent.futures.as_completed(future_to_request):
                    request = future_to_request[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Future execution failed: {e}")
                        results.append({
                            "status": "FAILED",
                            "error": str(e),
                            "request": request
                        })
            
            logger.info(f"Batch execution completed: {len(results)} workflows")
            return results
            
        except Exception as e:
            logger.error(f"Batch workflow execution failed: {e}")
            return [{
                "status": "FAILED",
                "error": str(e),
                "batch_size": len(workflow_requests)
            }]
    
    def resume_workflow(self, checkpoint_id: str) -> Dict[str, Any]:
        """Resume workflow execution from checkpoint"""
        try:
            return self.state_graph.resume_workflow(checkpoint_id)
        except Exception as e:
            logger.error(f"Failed to resume workflow from checkpoint {checkpoint_id}: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "checkpoint_id": checkpoint_id
            }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed workflow status"""
        try:
            # Get from active workflows first
            if workflow_id in self.active_workflows:
                return self.active_workflows[workflow_id]
            
            # Get from checkpointed workflows
            status = self.state_graph.get_workflow_status(workflow_id)
            if status:
                # Enhance with additional status information
                workflow_history = self.redis_checkpointer.get_workflow_history(workflow_id)
                latest_checkpoint = self.redis_checkpointer.list_workflows(
                    limit=1,
                    status_filter=status.get("status")
                )
                
                status.update({
                    "history": workflow_history,
                    "latest_checkpoint": latest_checkpoint[0] if latest_checkpoint else None
                })
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return None
    
    def list_workflows(
        self,
        status_filter: Optional[str] = None,
        limit: int = 50,
        sort_by: str = "timestamp"
    ) -> List[Dict[str, Any]]:
        """List workflows with filtering and sorting"""
        try:
            return self.redis_checkpointer.list_workflows(
                status_filter=status_filter,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []
    
    def cancel_workflow(self, workflow_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a running workflow"""
        try:
            success = self.state_graph.cancel_workflow(workflow_id)
            
            if success and workflow_id in self.active_workflows:
                self.active_workflows[workflow_id].update({
                    "status": "CANCELLED",
                    "cancel_reason": reason or "User cancellation",
                    "end_time": datetime.now()
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow and all associated data"""
        try:
            # Remove from active workflows
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            
            # Delete from Redis
            success = self.redis_checkpointer.delete_workflow(workflow_id)
            
            logger.info(f"Workflow deleted: {workflow_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            return False
    
    def get_workflow_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get complete execution history for a workflow"""
        try:
            return self.redis_checkpointer.get_workflow_history(workflow_id)
        except Exception as e:
            logger.error(f"Failed to get workflow history: {e}")
            return []
    
    def get_workflow_results(
        self, 
        workflow_id: str,
        include_intermediate: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get final results from a completed workflow
        
        Args:
            workflow_id: Workflow identifier
            include_intermediate: Include intermediate node results
            
        Returns:
            Dict containing workflow results or None
        """
        try:
            status = self.get_workflow_status(workflow_id)
            if not status:
                return None
            
            # Get latest checkpoint
            workflows = self.redis_checkpointer.list_workflows(
                status_filter=status.get("status"),
                limit=1
            )
            
            if not workflows:
                return None
            
            latest_checkpoint_id = workflows[0]["checkpoint_id"]
            workflow_state = self.redis_checkpointer.restore_checkpoint(latest_checkpoint_id)
            
            if not workflow_state:
                return None
            
            # Compile results
            results = {
                "workflow_id": workflow_id,
                "status": workflow_state.status.value,
                "symbol": workflow_state.metadata.get("symbol"),
                "strategy": workflow_state.metadata.get("strategy"),
                "execution_time": (
                    workflow_state.end_time - workflow_state.start_time
                    if workflow_state.end_time else None
                ),
                "final_decision": workflow_state.ml_prediction.decision.value if workflow_state.ml_prediction else None,
                "confidence": workflow_state.prediction_confidence,
                "risk_assessment": asdict(workflow_state.risk_assessment) if workflow_state.risk_assessment else None,
                "execution_result": workflow_state.execution_result,
                "market_data": asdict(workflow_state.market_data) if workflow_state.market_data else None,
                "metadata": workflow_state.metadata
            }
            
            # Include intermediate results if requested
            if include_intermediate:
                node_results = self.redis_checkpointer.get_node_results(workflow_id)
                results["intermediate_results"] = node_results
                results["execution_history"] = workflow_state.execution_history
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get workflow results: {e}")
            return None
    
    def register_workflow_callback(self, workflow_id: str, callback: Callable) -> None:
        """Register a callback function for workflow completion"""
        if workflow_id not in self.workflow_callbacks:
            self.workflow_callbacks[workflow_id] = []
        self.workflow_callbacks[workflow_id].append(callback)
    
    def cleanup_expired_workflows(self, max_age_hours: int = 24) -> int:
        """Clean up expired workflows"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # Get all completed/failed workflows
            workflows = self.redis_checkpointer.list_workflows(limit=1000)
            
            cleaned_count = 0
            for workflow in workflows:
                try:
                    workflow_time = datetime.fromisoformat(workflow["timestamp"])
                    if workflow_time < cutoff_time:
                        workflow_id = workflow["workflow_id"]
                        self.delete_workflow(workflow_id)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to clean workflow {workflow.get('workflow_id')}: {e}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} expired workflows")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired workflows: {e}")
            return 0
    
    def get_workflow_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get workflow execution metrics"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
            workflows = self.list_workflows(limit=1000)
            
            # Filter by time range
            recent_workflows = []
            for workflow in workflows:
                try:
                    workflow_time = datetime.fromisoformat(workflow["timestamp"])
                    if workflow_time >= cutoff_time:
                        recent_workflows.append(workflow)
                except Exception:
                    continue
            
            # Calculate metrics
            total_workflows = len(recent_workflows)
            completed_workflows = len([w for w in recent_workflows if w["status"] == "completed"])
            failed_workflows = len([w for w in recent_workflows if w["status"] == "failed"])
            
            success_rate = (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0
            
            # Status distribution
            status_distribution = {}
            for workflow in recent_workflows:
                status = workflow["status"]
                status_distribution[status] = status_distribution.get(status, 0) + 1
            
            return {
                "time_range_hours": time_range_hours,
                "total_workflows": total_workflows,
                "completed_workflows": completed_workflows,
                "failed_workflows": failed_workflows,
                "success_rate": success_rate,
                "status_distribution": status_distribution,
                "cleanup_needed": len([w for w in recent_workflows 
                                     if datetime.fromisoformat(w["timestamp"]) < cutoff_time])
            }
            
        except Exception as e:
            logger.error(f"Failed to get workflow metrics: {e}")
            return {}
    
    def _execute_workflow_callbacks(self, workflow_id: str, result: Dict[str, Any]) -> None:
        """Execute registered callbacks for a workflow"""
        if workflow_id in self.workflow_callbacks:
            for callback in self.workflow_callbacks[workflow_id]:
                try:
                    callback(workflow_id, result)
                except Exception as e:
                    logger.error(f"Callback execution failed: {e}")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for trading workflow"""
        return {
            "auto_checkpoint": True,
            "checkpoint_interval": 300,  # 5 minutes
            "max_workflow_duration": 1800,  # 30 minutes
            "retry_failed_nodes": True,
            "max_retries": 3,
            "enable_callbacks": True,
            "batch_size": 10,
            "timeout": 600,  # 10 minutes
            "risk_config": {
                "max_position_size": 0.20,
                "max_portfolio_risk": 0.10,
                "confidence_threshold": 0.6
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on workflow system"""
        try:
            # Check Redis connection
            redis_healthy = self.redis_checkpointer.ping()
            
            # Check active workflows
            active_count = len(self.active_workflows)
            
            # Get recent metrics
            metrics = self.get_workflow_metrics(time_range_hours=1)
            
            return {
                "status": "healthy" if redis_healthy else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "redis_connection": redis_healthy,
                "active_workflows": active_count,
                "recent_metrics": metrics,
                "components": {
                    "redis_checkpointer": "ok",
                    "state_graph": "ok",
                    "workflow_manager": "ok"
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }