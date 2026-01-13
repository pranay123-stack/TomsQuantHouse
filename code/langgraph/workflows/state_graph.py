"""
Trading StateGraph
Main LangGraph workflow definition with conditional routing logic
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint import Checkpointer

from .state import WorkflowState, TradingWorkflowState, WorkflowStatus
from .nodes import MarketAnalysisNode, MLPredictionNode, RiskManagementNode, ExecutionNode
from ..checkpoints.redis_checkpointer import RedisCheckpointer

logger = logging.getLogger(__name__)

class TradingStateGraph:
    """
    Main StateGraph for trading workflow orchestration
    Handles market analysis, ML predictions, risk management, and execution
    """
    
    def __init__(
        self, 
        redis_checkpointer: RedisCheckpointer,
        market_data_source=None,
        ml_model_registry=None,
        execution_engine=None,
        risk_config=None
    ):
        """
        Initialize the trading StateGraph
        
        Args:
            redis_checkpointer: Redis-based checkpointing system
            market_data_source: Market data provider
            ml_model_registry: ML model registry
            execution_engine: Trading execution engine
            risk_config: Risk management configuration
        """
        self.redis_checkpointer = redis_checkpointer
        self.checkpointer = redis_checkpointer  # LangGraph compatibility
        
        # Initialize workflow nodes
        self.market_analysis_node = MarketAnalysisNode(market_data_source)
        self.ml_prediction_node = MLPredictionNode(ml_model_registry)
        self.risk_management_node = RiskManagementNode(risk_config)
        self.execution_node = ExecutionNode(execution_engine)
        
        # Build the workflow graph
        self.workflow = self._build_workflow_graph()
        
        # Track active workflows
        self.active_workflows: Dict[str, str] = {}
        
        logger.info("Trading StateGraph initialized")
    
    def _build_workflow_graph(self) -> StateGraph:
        """Build the workflow graph with nodes and conditional routing"""
        
        # Create the graph with our state type
        workflow = StateGraph(TradingWorkflowState)
        
        # Add nodes
        workflow.add_node("market_analysis", self._market_analysis_node)
        workflow.add_node("ml_prediction", self._ml_prediction_node)
        workflow.add_node("risk_management", self._risk_management_node)
        workflow.add_node("execution", self._execution_node)
        workflow.add_node("risk_review", self._risk_review_node)
        workflow.add_node("error_handling", self._error_handling_node)
        workflow.add_node("completion", self._completion_node)
        
        # Set entry point
        workflow.set_entry_point("market_analysis")
        
        # Add edges with conditional routing
        workflow.add_conditional_edges(
            "market_analysis",
            self._route_after_market_analysis,
            {
                "ml_prediction": "ml_prediction",
                "error_handling": "error_handling"
            }
        )
        
        workflow.add_conditional_edges(
            "ml_prediction",
            self._route_after_ml_prediction,
            {
                "risk_management": "risk_management",
                "error_handling": "error_handling"
            }
        )
        
        workflow.add_conditional_edges(
            "risk_management",
            self._route_after_risk_management,
            {
                "execution": "execution",
                "risk_review": "risk_review",
                "error_handling": "error_handling"
            }
        )
        
        workflow.add_edge("risk_review", "risk_management")
        workflow.add_edge("execution", "completion")
        workflow.add_edge("error_handling", "completion")
        workflow.add_edge("completion", END)
        
        return workflow
    
    def compile(self) -> Callable:
        """Compile the workflow for execution"""
        return self.workflow.compile()
    
    def execute_workflow(
        self, 
        workflow_id: str,
        symbol: str,
        metadata: Optional[Dict[str, Any]] = None,
        checkpoint: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a complete trading workflow
        
        Args:
            workflow_id: Unique workflow identifier
            symbol: Trading symbol (e.g., BTCUSDT)
            metadata: Additional workflow metadata
            checkpoint: Whether to create checkpoints
            
        Returns:
            Dict[str, Any]: Workflow execution result
        """
        try:
            # Create execution ID
            execution_id = str(uuid.uuid4())
            
            # Initialize workflow state
            initial_state = self._create_initial_state(
                workflow_id=workflow_id,
                execution_id=execution_id,
                symbol=symbol,
                metadata=metadata or {}
            )
            
            # Register active workflow
            self.active_workflows[workflow_id] = execution_id
            
            logger.info(f"Starting workflow execution: {workflow_id}")
            
            # Compile and execute workflow
            compiled_workflow = self.compile()
            
            # Execute with checkpointing if enabled
            if checkpoint:
                config = {"configurable": {"thread_id": workflow_id}}
                result = compiled_workflow.invoke(initial_state, config)
            else:
                result = compiled_workflow.invoke(initial_state)
            
            # Clean up active workflow tracking
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            
            logger.info(f"Workflow execution completed: {workflow_id}")
            return result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            
            # Clean up on error
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            
            return {
                "status": "FAILED",
                "error": str(e),
                "workflow_id": workflow_id,
                "execution_id": execution_id
            }
    
    def resume_workflow(
        self, 
        checkpoint_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resume workflow execution from a checkpoint
        
        Args:
            checkpoint_id: Checkpoint identifier
            config: Execution configuration
            
        Returns:
            Dict[str, Any]: Resumed workflow result
        """
        try:
            logger.info(f"Resuming workflow from checkpoint: {checkpoint_id}")
            
            # Restore state from checkpoint
            state = self.redis_checkpointer.restore_checkpoint(checkpoint_id)
            if not state:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")
            
            # Compile workflow
            compiled_workflow = self.compile()
            
            # Resume execution
            workflow_config = config or {"configurable": {"thread_id": state.workflow_id}}
            result = compiled_workflow.invoke(state.__dict__, workflow_config)
            
            logger.info(f"Workflow resumed successfully: {checkpoint_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to resume workflow from checkpoint {checkpoint_id}: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "checkpoint_id": checkpoint_id
            }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow"""
        try:
            workflows = self.redis_checkpointer.list_workflows()
            for workflow in workflows:
                if workflow["workflow_id"] == workflow_id:
                    return workflow
            return None
        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return None
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        try:
            # Remove from active workflows
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            
            # Update workflow status in checkpoint
            workflows = self.redis_checkpointer.list_workflows(limit=1000)
            for workflow in workflows:
                if workflow["workflow_id"] == workflow_id:
                    # Find the latest checkpoint
                    checkpoint_id = workflow["checkpoint_id"]
                    state = self.redis_checkpointer.restore_checkpoint(checkpoint_id)
                    if state:
                        state.status = WorkflowStatus.CANCELLED
                        state.end_time = datetime.now()
                        self.redis_checkpointer.create_checkpoint(
                            workflow_id, state, "cancellation"
                        )
                    break
            
            logger.info(f"Workflow cancelled: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False
    
    # =============================================================================
    # NODE IMPLEMENTATIONS
    # =============================================================================
    
    def _market_analysis_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """Market analysis node implementation"""
        try:
            # Convert to WorkflowState for node execution
            workflow_state = self._dict_to_workflow_state(state)
            
            # Execute market analysis
            result = self.market_analysis_node.execute(workflow_state)
            
            # Create checkpoint if requested
            if result.checkpoint:
                checkpoint_id = self.redis_checkpointer.create_checkpoint(
                    state["workflow_id"], workflow_state, "market_analysis"
                )
            
            # Update state with result
            self._update_state_with_result(state, result, workflow_state)
            
            return state
            
        except Exception as e:
            logger.error(f"Market analysis node failed: {e}")
            state["error_log"].append(f"Market analysis failed: {str(e)}")
            return state
    
    def _ml_prediction_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """ML prediction node implementation"""
        try:
            workflow_state = self._dict_to_workflow_state(state)
            
            result = self.ml_prediction_node.execute(workflow_state)
            
            if result.checkpoint:
                checkpoint_id = self.redis_checkpointer.create_checkpoint(
                    state["workflow_id"], workflow_state, "ml_prediction"
                )
            
            self._update_state_with_result(state, result, workflow_state)
            
            return state
            
        except Exception as e:
            logger.error(f"ML prediction node failed: {e}")
            state["error_log"].append(f"ML prediction failed: {str(e)}")
            return state
    
    def _risk_management_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """Risk management node implementation"""
        try:
            workflow_state = self._dict_to_workflow_state(state)
            
            result = self.risk_management_node.execute(workflow_state)
            
            if result.checkpoint:
                checkpoint_id = self.redis_checkpointer.create_checkpoint(
                    state["workflow_id"], workflow_state, "risk_management"
                )
            
            self._update_state_with_result(state, result, workflow_state)
            
            return state
            
        except Exception as e:
            logger.error(f"Risk management node failed: {e}")
            state["error_log"].append(f"Risk management failed: {str(e)}")
            return state
    
    def _execution_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """Execution node implementation"""
        try:
            workflow_state = self._dict_to_workflow_state(state)
            
            result = self.execution_node.execute(workflow_state)
            
            if result.checkpoint:
                checkpoint_id = self.redis_checkpointer.create_checkpoint(
                    state["workflow_id"], workflow_state, "execution"
                )
            
            self._update_state_with_result(state, result, workflow_state)
            
            return state
            
        except Exception as e:
            logger.error(f"Execution node failed: {e}")
            state["error_log"].append(f"Execution failed: {str(e)}")
            return state
    
    def _risk_review_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """Risk review node implementation for manual override"""
        try:
            # This node could integrate with human-in-the-loop workflows
            # For now, it just adds a checkpoint and continues
            workflow_state = self._dict_to_workflow_state(state)
            
            # Manual risk review (could be extended to human oversight)
            state["metadata"]["manual_review_required"] = False  # Set to True for manual review
            state["metadata"]["review_timestamp"] = datetime.now().isoformat()
            
            logger.info("Risk review completed - proceeding to execution")
            
            return state
            
        except Exception as e:
            logger.error(f"Risk review node failed: {e}")
            state["error_log"].append(f"Risk review failed: {str(e)}")
            return state
    
    def _error_handling_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """Error handling node implementation"""
        try:
            # Log the error and prepare for recovery
            logger.error(f"Handling workflow errors for {state['workflow_id']}")
            
            # Mark workflow as failed
            state["status"] = WorkflowStatus.FAILED.value
            state["end_time"] = datetime.now().isoformat()
            
            # Create final checkpoint
            workflow_state = self._dict_to_workflow_state(state)
            checkpoint_id = self.redis_checkpointer.create_checkpoint(
                state["workflow_id"], workflow_state, "error_handling"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error handling node failed: {e}")
            return state
    
    def _completion_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """Completion node implementation"""
        try:
            # Mark workflow as completed
            state["status"] = WorkflowStatus.COMPLETED.value
            state["end_time"] = datetime.now().isoformat()
            
            # Create final checkpoint
            workflow_state = self._dict_to_workflow_state(state)
            checkpoint_id = self.redis_checkpointer.create_checkpoint(
                state["workflow_id"], workflow_state, "completion"
            )
            
            logger.info(f"Workflow {state['workflow_id']} completed successfully")
            
            return state
            
        except Exception as e:
            logger.error(f"Completion node failed: {e}")
            return state
    
    # =============================================================================
    # CONDITIONAL ROUTING FUNCTIONS
    # =============================================================================
    
    def _route_after_market_analysis(self, state: TradingWorkflowState) -> str:
        """Route logic after market analysis"""
        if not state.get("market_data"):
            return "error_handling"
        return "ml_prediction"
    
    def _route_after_ml_prediction(self, state: TradingWorkflowState) -> str:
        """Route logic after ML prediction"""
        if not state.get("ml_prediction"):
            return "error_handling"
        return "risk_management"
    
    def _route_after_risk_management(self, state: TradingWorkflowState) -> str:
        """Route logic after risk management"""
        risk_score = state.get("risk_score", 0)
        
        if risk_score >= 3:  # High risk
            return "risk_review"
        else:
            return "execution"
    
    # =============================================================================
    # UTILITY FUNCTIONS
    # =============================================================================
    
    def _create_initial_state(
        self, 
        workflow_id: str, 
        execution_id: str, 
        symbol: str, 
        metadata: Dict[str, Any]
    ) -> TradingWorkflowState:
        """Create initial workflow state"""
        return TradingWorkflowState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            status=WorkflowStatus.PENDING,
            current_node="",
            market_data=None,
            market_condition=None,
            ml_prediction=None,
            prediction_confidence=0.0,
            risk_assessment=None,
            execution_order=None,
            execution_history=[],
            node_history=[],
            error_log=[],
            metadata={
                "symbol": symbol,
                **metadata
            },
            checkpoint_id=None
        )
    
    def _dict_to_workflow_state(self, state_dict: TradingWorkflowState) -> WorkflowState:
        """Convert LangGraph state dict to WorkflowState"""
        # This would need proper conversion based on your state structure
        # For now, return a basic WorkflowState
        return WorkflowState(
            workflow_id=state_dict["workflow_id"],
            execution_id=state_dict["execution_id"],
            status=WorkflowStatus(state_dict["status"]),
            start_time=datetime.now(),
            current_node=state_dict.get("current_node", ""),
            metadata=state_dict.get("metadata", {})
        )
    
    def _update_state_with_result(
        self, 
        state: TradingWorkflowState, 
        result, 
        workflow_state: WorkflowState
    ) -> None:
        """Update LangGraph state with node execution result"""
        # This would update the state with the result data
        # Implementation depends on specific state structure
        pass