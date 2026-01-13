"""
Comprehensive tests for the LangGraph workflow system
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Import LangGraph components
try:
    from ..workflows.trading_workflow import TradingWorkflow
    from ..workflows.state_graph import TradingStateGraph
    from ..workflows.state import WorkflowState, WorkflowStatus, DecisionOutcome, RiskLevel
    from ..checkpoints.redis_checkpointer import RedisCheckpointer
    from ..visualization.monitoring import WorkflowVisualization, WorkflowMonitoring
    from ..utils.workflow_utils import WorkflowUtils
    from ..api.workflow_api import create_workflow_api
except ImportError as e:
    pytest.skip(f"Could not import LangGraph components: {e}", allow_module_level=True)

# Mock Redis client for testing
class MockRedisClient:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self.data = {}
        self.db = 0
    
    def select(self, db):
        self.db = db
    
    def setex(self, key, ttl, value):
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        self.data[key] = value
        return True
    
    def get(self, key):
        value = self.data.get(key)
        if value and isinstance(value, str):
            return value.encode('utf-8')
        return value
    
    def delete(self, key):
        return self.data.pop(key, None)
    
    def keys(self, pattern):
        keys = [k.encode('utf-8') if isinstance(k, str) else k for k in self.data.keys()]
        return keys
    
    def ping(self):
        return True
    
    def ttl(self, key):
        return 3600
    
    def expire(self, key, ttl):
        return True
    
    def close(self):
        pass
    
    def sadd(self, key, value):
        if key not in self.data:
            self.data[key] = set()
        self.data[key].add(value)
        return True
    
    def smembers(self, key):
        if key in self.data and isinstance(self.data[key], set):
            return {v.encode('utf-8') if isinstance(v, str) else v for v in self.data[key]}
        return set()
    
    def flushdb(self):
        self.data.clear()
        return True
    
    def info(self, section):
        return {"used_memory_human": "1M"}

class TestRedisCheckpointer:
    """Test Redis checkpointer functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.redis_client = MockRedisClient()
        self.checkpointer = RedisCheckpointer(self.redis_client)
    
    def test_create_checkpoint(self):
        """Test creating a checkpoint"""
        state = WorkflowState(
            workflow_id="test_workflow",
            execution_id="test_exec",
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
            current_node="market_analysis",
            metadata={"symbol": "BTCUSDT"}
        )
        
        checkpoint_id = self.checkpointer.create_checkpoint(
            workflow_id="test_workflow",
            state=state,
            node_name="market_analysis"
        )
        
        assert checkpoint_id is not None
        assert len(checkpoint_id) > 0
    
    def test_restore_checkpoint(self):
        """Test restoring from checkpoint"""
        state = WorkflowState(
            workflow_id="test_workflow",
            execution_id="test_exec",
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
            current_node="market_analysis",
            metadata={"symbol": "BTCUSDT"}
        )
        
        # Create checkpoint
        checkpoint_id = self.checkpointer.create_checkpoint(
            workflow_id="test_workflow",
            state=state,
            node_name="market_analysis"
        )
        
        # Restore checkpoint
        restored_state = self.checkpointer.restore_checkpoint(checkpoint_id)
        
        assert restored_state is not None
        assert restored_state.workflow_id == "test_workflow"
        assert restored_state.current_node == "market_analysis"
    
    def test_list_workflows(self):
        """Test listing workflows"""
        # Create some test workflows
        state1 = WorkflowState(
            workflow_id="workflow_1",
            execution_id="exec_1",
            status=WorkflowStatus.COMPLETED,
            start_time=datetime.now(),
            metadata={"symbol": "BTCUSDT"}
        )
        
        state2 = WorkflowState(
            workflow_id="workflow_2",
            execution_id="exec_2",
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
            metadata={"symbol": "ETHUSDT"}
        )
        
        self.checkpointer.create_checkpoint("workflow_1", state1, "completion")
        self.checkpointer.create_checkpoint("workflow_2", state2, "risk_management")
        
        # List all workflows
        workflows = self.checkpointer.list_workflows()
        assert len(workflows) >= 2
        
        # List by status
        completed_workflows = self.checkpointer.list_workflows(status_filter="completed")
        assert len(completed_workflows) >= 1
    
    def test_delete_workflow(self):
        """Test deleting a workflow"""
        state = WorkflowState(
            workflow_id="delete_test",
            execution_id="exec_delete",
            status=WorkflowStatus.COMPLETED,
            start_time=datetime.now(),
            metadata={"symbol": "ADAUSDT"}
        )
        
        # Create workflow
        checkpoint_id = self.checkpointer.create_checkpoint("delete_test", state, "completion")
        
        # Delete workflow
        success = self.checkpointer.delete_workflow("delete_test")
        assert success is True
        
        # Verify deletion
        restored_state = self.checkpointer.restore_checkpoint(checkpoint_id)
        assert restored_state is None


class TestTradingWorkflow:
    """Test trading workflow functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.redis_client = MockRedisClient()
        self.checkpointer = RedisCheckpointer(self.redis_client)
        self.workflow = TradingWorkflow(self.checkpointer)
    
    def test_execute_workflow(self):
        """Test basic workflow execution"""
        result = self.workflow.execute_trading_workflow(
            symbol="BTCUSDT",
            strategy="momentum",
            metadata={"test_mode": True}
        )
        
        assert result["workflow_id"] is not None
        assert result["status"] in ["completed", "FAILED"]
    
    def test_batch_execution(self):
        """Test batch workflow execution"""
        workflow_requests = [
            {"symbol": "BTCUSDT", "strategy": "momentum"},
            {"symbol": "ETHUSDT", "strategy": "mean_reversion"},
            {"symbol": "ADAUSDT", "strategy": "trend_following"}
        ]
        
        results = self.workflow.batch_execute_workflows(
            workflow_requests=workflow_requests,
            max_concurrent=3
        )
        
        assert len(results) == 3
        for result in results:
            assert result["workflow_id"] is not None
            assert result["status"] in ["completed", "FAILED"]
    
    def test_get_workflow_status(self):
        """Test getting workflow status"""
        # Execute a workflow first
        result = self.workflow.execute_trading_workflow(
            symbol="BTCUSDT",
            strategy="momentum"
        )
        
        workflow_id = result["workflow_id"]
        
        # Get status
        status = self.workflow.get_workflow_status(workflow_id)
        assert status is not None
        assert status["workflow_id"] == workflow_id
    
    def test_health_check(self):
        """Test system health check"""
        health = self.workflow.health_check()
        
        assert health["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in health
        assert "redis_connection" in health
    
    def test_cleanup_expired_workflows(self):
        """Test cleaning up expired workflows"""
        # This test might not show cleanup in mock environment
        # but tests the method existence and basic functionality
        cleaned_count = self.workflow.cleanup_expired_workflows(max_age_hours=1)
        assert isinstance(cleaned_count, int)


class TestWorkflowUtils:
    """Test workflow utility functions"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.utils = WorkflowUtils()
    
    def test_validate_workflow_state(self):
        """Test workflow state validation"""
        # Valid state
        valid_state = {
            "workflow_id": "test_123",
            "execution_id": "exec_456",
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "current_node": "market_analysis",
            "metadata": {"symbol": "BTCUSDT"}
        }
        
        is_valid, errors = self.utils.validate_workflow_state(valid_state)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid state
        invalid_state = {
            "workflow_id": "test_123"
            # Missing required fields
        }
        
        is_valid, errors = self.utils.validate_workflow_state(invalid_state)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_format_workflow_summary(self):
        """Test workflow summary formatting"""
        state = {
            "workflow_id": "test_123",
            "status": "completed",
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "current_node": "completion",
            "metadata": {"symbol": "BTCUSDT", "strategy": "momentum"}
        }
        
        summary = self.utils.format_workflow_summary(state)
        
        assert summary["workflow_id"] == "test_123"
        assert summary["status"] == "completed"
        assert summary["symbol"] == "BTCUSDT"
        assert summary["progress"] == 100
    
    def test_calculate_workflow_statistics(self):
        """Test workflow statistics calculation"""
        workflows = [
            {"status": "completed", "start_time": datetime.now().isoformat()},
            {"status": "completed", "start_time": datetime.now().isoformat()},
            {"status": "failed", "start_time": datetime.now().isoformat()},
            {"status": "running", "start_time": datetime.now().isoformat()}
        ]
        
        stats = self.utils.calculate_workflow_statistics(workflows)
        
        assert stats["total_count"] == 4
        assert stats["success_rate"] == 0.5  # 2 completed out of 4
        assert "status_distribution" in stats
    
    def test_export_workflow_data(self):
        """Test workflow data export"""
        state = {
            "workflow_id": "test_123",
            "status": "completed",
            "metadata": {"symbol": "BTCUSDT"}
        }
        
        # JSON export
        json_data = self.utils.export_workflow_data("test_123", state, "json")
        assert isinstance(json_data, str)
        assert '"workflow_id": "test_123"' in json_data
        
        # Dict export (should return the original data)
        dict_data = self.utils.export_workflow_data("test_123", state, "csv")  # Will fallback to original
        assert isinstance(dict_data, dict)
    
    def test_generate_workflow_id(self):
        """Test workflow ID generation"""
        workflow_id = self.utils.generate_workflow_id("BTCUSDT", "momentum")
        
        assert workflow_id.startswith("trading_BTCUSDT_momentum_")
        assert len(workflow_id) > 30  # Should include timestamp and unique ID
    
    def test_parse_workflow_id(self):
        """Test workflow ID parsing"""
        workflow_id = "trading_BTCUSDT_momentum_1234567890_abc123"
        
        parsed = self.utils.parse_workflow_id(workflow_id)
        
        assert parsed is not None
        assert parsed["prefix"] == "trading"
        assert parsed["symbol"] == "BTCUSDT"
        assert parsed["strategy"] == "momentum"
        assert parsed["timestamp"] == "1234567890"


class TestWorkflowVisualization:
    """Test workflow visualization functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.redis_client = MockRedisClient()
        self.checkpointer = RedisCheckpointer(self.redis_client)
        self.visualization = WorkflowVisualization(self.checkpointer)
    
    def test_generate_workflow_graph_mermaid(self):
        """Test Mermaid graph generation"""
        mermaid_code = self.visualization.generate_workflow_graph_mermaid()
        
        assert "graph TD" in mermaid_code
        assert "MarketAnalysis" in mermaid_code
        assert "MLPrediction" in mermaid_code
        assert "RiskManagement" in mermaid_code
        assert "Execution" in mermaid_code
    
    def test_generate_execution_metrics_chart(self):
        """Test execution metrics generation"""
        metrics = self.visualization.generate_execution_metrics_chart(time_range_hours=24)
        
        assert "total_workflows" in metrics
        assert "status_distribution" in metrics
        assert "execution_times" in metrics
        assert metrics["type"] == "metrics_overview"


class TestWorkflowMonitoring:
    """Test workflow monitoring functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.redis_client = MockRedisClient()
        self.checkpointer = RedisCheckpointer(self.redis_client)
        self.monitoring = WorkflowMonitoring(self.checkpointer)
    
    def test_get_real_time_status(self):
        """Test real-time status retrieval"""
        status = self.monitoring.get_real_time_status()
        
        assert "total_workflows" in status
        assert "by_status" in status
        assert "alerts" in status
        assert "health_score" in status
    
    def test_check_alert_conditions(self):
        """Test alert condition checking"""
        workflows = [
            {"status": "failed", "timestamp": datetime.now().isoformat()},
            {"status": "failed", "timestamp": datetime.now().isoformat()},
            {"status": "completed", "timestamp": datetime.now().isoformat()}
        ]
        
        alerts = self.monitoring._check_alert_conditions(workflows)
        assert isinstance(alerts, list)
    
    def test_calculate_health_score(self):
        """Test health score calculation"""
        workflows = [
            {"status": "completed", "timestamp": datetime.now().isoformat()},
            {"status": "completed", "timestamp": datetime.now().isoformat()},
            {"status": "failed", "timestamp": datetime.now().isoformat()}
        ]
        
        alerts = []  # No alerts
        health_score = self.monitoring._calculate_health_score(workflows, alerts)
        
        assert isinstance(health_score, int)
        assert 0 <= health_score <= 100


class TestWorkflowIntegration:
    """Integration tests for complete workflow system"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.redis_client = MockRedisClient()
        self.checkpointer = RedisCheckpointer(self.redis_client)
        self.workflow = TradingWorkflow(self.checkpointer)
        self.utils = WorkflowUtils()
    
    def test_complete_workflow_lifecycle(self):
        """Test complete workflow lifecycle"""
        # 1. Execute workflow
        result = self.workflow.execute_trading_workflow(
            symbol="BTCUSDT",
            strategy="momentum",
            metadata={"integration_test": True}
        )
        
        assert result["workflow_id"] is not None
        
        workflow_id = result["workflow_id"]
        
        # 2. Get status
        status = self.workflow.get_workflow_status(workflow_id)
        assert status is not None
        
        # 3. Get results
        results = self.workflow.get_workflow_results(workflow_id)
        assert results is not None
        
        # 4. Get history
        history = self.workflow.get_workflow_history(workflow_id)
        assert isinstance(history, list)
    
    def test_workflow_with_checkpointing(self):
        """Test workflow with checkpointing"""
        # Create initial state with checkpointing
        state = WorkflowState(
            workflow_id="checkpoint_test",
            execution_id="exec_checkpoint",
            status=WorkflowStatus.RUNNING,
            start_time=datetime.now(),
            current_node="market_analysis",
            metadata={"symbol": "ETHUSDT"}
        )
        
        # Create checkpoint
        checkpoint_id = self.checkpointer.create_checkpoint(
            workflow_id="checkpoint_test",
            state=state,
            node_name="market_analysis"
        )
        
        assert checkpoint_id is not None
        
        # Resume from checkpoint
        resumed_state = self.checkpointer.restore_checkpoint(checkpoint_id)
        assert resumed_state is not None
        assert resumed_state.workflow_id == "checkpoint_test"
    
    def test_workflow_analytics(self):
        """Test workflow analytics functionality"""
        # Execute multiple workflows
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        for symbol in symbols:
            self.workflow.execute_trading_workflow(
                symbol=symbol,
                strategy="momentum"
            )
        
        # Generate statistics
        all_workflows = self.checkpointer.list_workflows(limit=100)
        stats = self.utils.calculate_workflow_statistics(all_workflows)
        
        assert stats["total_count"] >= 3
        assert "success_rate" in stats
        
        # Generate report
        report = self.utils.generate_workflow_report(all_workflows)
        assert "statistics" in report
        assert "recommendations" in report


# Test configuration and fixtures
@pytest.fixture
def mock_redis_client():
    """Fixture for mock Redis client"""
    return MockRedisClient()

@pytest.fixture
def sample_workflow_state():
    """Fixture for sample workflow state"""
    return WorkflowState(
        workflow_id="test_workflow_123",
        execution_id="exec_456",
        status=WorkflowStatus.RUNNING,
        start_time=datetime.now(),
        current_node="market_analysis",
        metadata={"symbol": "BTCUSDT", "strategy": "momentum"}
    )

@pytest.fixture
def sample_workflows():
    """Fixture for sample workflow data"""
    return [
        {
            "workflow_id": "workflow_1",
            "status": "completed",
            "start_time": datetime.now().isoformat(),
            "metadata": {"symbol": "BTCUSDT"}
        },
        {
            "workflow_id": "workflow_2",
            "status": "completed",
            "start_time": datetime.now().isoformat(),
            "metadata": {"symbol": "ETHUSDT"}
        },
        {
            "workflow_id": "workflow_3",
            "status": "failed",
            "start_time": datetime.now().isoformat(),
            "metadata": {"symbol": "ADAUSDT"}
        }
    ]

# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )

# Test runners for different test types
def test_run_unit_tests():
    """Run unit tests"""
    pytest.main(["-v", "-m", "unit", __file__])

def test_run_integration_tests():
    """Run integration tests"""
    pytest.main(["-v", "-m", "integration", __file__])

def test_run_all_tests():
    """Run all tests"""
    pytest.main(["-v", __file__])

if __name__ == "__main__":
    # Run tests directly
    test_run_all_tests()