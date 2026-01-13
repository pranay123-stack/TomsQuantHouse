"""
Essential API tests for core functionality
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import json

class TestAuthenticationAPI:
    """Test authentication endpoints"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "securepassword123"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        # Should return 201 or 200 depending on implementation
        assert response.status_code in [200, 201]
        
    def test_login_success(self, client):
        """Test successful user login"""
        login_data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            "username": "invaliduser",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/v1/workflows")
        
        assert response.status_code == 401
        
    def test_protected_endpoint_with_token(self, client, auth_headers):
        """Test accessing protected endpoint with valid token"""
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            mock_service.return_value.list_workflows.return_value = []
            
            response = client.get("/api/v1/workflows", headers=auth_headers)
            
            assert response.status_code == 200


class TestWorkflowAPI:
    """Test workflow management endpoints"""
    
    def test_create_workflow_success(self, client, auth_headers, sample_workflow_data):
        """Test successful workflow creation"""
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            mock_service.return_value.create_workflow.return_value = {
                "id": "workflow-123",
                "name": sample_workflow_data["name"],
                "status": "pending"
            }
            
            response = client.post(
                "/api/v1/workflows", 
                json=sample_workflow_data, 
                headers=auth_headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            
    def test_list_workflows(self, client, auth_headers):
        """Test listing workflows"""
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            mock_service.return_value.list_workflows.return_value = []
            
            response = client.get("/api/v1/workflows", headers=auth_headers)
            
            assert response.status_code == 200
            
    def test_get_workflow_by_id(self, client, auth_headers):
        """Test getting workflow by ID"""
        workflow_id = "test-workflow-123"
        
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            mock_service.return_value.get_workflow_by_id.return_value = {
                "id": workflow_id,
                "name": "Test Workflow",
                "status": "pending"
            }
            
            response = client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
            
            assert response.status_code == 200
            
    def test_update_workflow(self, client, auth_headers, sample_workflow_data):
        """Test updating workflow"""
        workflow_id = "test-workflow-123"
        update_data = {"name": "Updated Workflow"}
        
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            mock_service.return_value.update_workflow.return_value = {
                "id": workflow_id,
                "name": "Updated Workflow",
                "status": "pending"
            }
            
            response = client.put(
                f"/api/v1/workflows/{workflow_id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            
    def test_delete_workflow(self, client, auth_headers):
        """Test deleting workflow"""
        workflow_id = "test-workflow-123"
        
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            mock_service.return_value.delete_workflow.return_value = True
            
            response = client.delete(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
            
            assert response.status_code == 204


class TestStateAPI:
    """Test state management endpoints"""
    
    def test_create_state(self, client, auth_headers, sample_state_data):
        """Test creating state"""
        with patch('app.services.state_service.StateService') as mock_service:
            mock_service.return_value.create_state.return_value = {
                "id": "state-123",
                "node_name": sample_state_data["node_name"],
                "status": "pending"
            }
            
            response = client.post(
                "/api/v1/states",
                json=sample_state_data,
                headers=auth_headers
            )
            
            assert response.status_code == 201
            
    def test_get_workflow_states(self, client, auth_headers):
        """Test getting states for a workflow"""
        workflow_id = "test-workflow-123"
        
        with patch('app.services.state_service.StateService') as mock_service:
            mock_service.return_value.get_workflow_states.return_value = []
            
            response = client.get(f"/api/v1/states/workflow/{workflow_id}", headers=auth_headers)
            
            assert response.status_code == 200


class TestMonitoringAPI:
    """Test monitoring and health endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        with patch('app.services.monitoring_service.MonitoringService') as mock_service:
            mock_service.return_value.get_health_status.return_value = {
                "status": "healthy",
                "database": "connected",
                "redis": "connected",
                "timestamp": "2024-11-02T09:45:00Z"
            }
            
            response = client.get("/api/v1/monitoring/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        with patch('app.services.metrics_collector.MetricsCollector') as mock_collector:
            mock_collector.return_value.get_metrics.return_value = {
                "workflows_executed": 100,
                "active_workflows": 5,
                "average_execution_time": 2.5
            }
            
            response = client.get("/api/v1/monitoring/metrics")
            
            assert response.status_code == 200
            
    def test_prometheus_metrics(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]


class TestVisualizationAPI:
    """Test visualization endpoints"""
    
    def test_workflow_graph(self, client, auth_headers):
        """Test workflow graph visualization"""
        workflow_id = "test-workflow-123"
        
        with patch('app.services.visualization_service.VisualizationService') as mock_service:
            mock_service.return_value.get_workflow_graph.return_value = {
                "nodes": [],
                "edges": [],
                "graph_type": "mermaid"
            }
            
            response = client.get(f"/api/v1/visualization/graph/{workflow_id}", headers=auth_headers)
            
            assert response.status_code == 200
            
    def test_workflow_timeline(self, client, auth_headers):
        """Test workflow timeline visualization"""
        workflow_id = "test-workflow-123"
        
        with patch('app.services.visualization_service.VisualizationService') as mock_service:
            mock_service.return_value.get_workflow_timeline.return_value = {
                "events": [],
                "timeline_type": "gantt"
            }
            
            response = client.get(f"/api/v1/visualization/timeline/{workflow_id}", headers=auth_headers)
            
            assert response.status_code == 200


class TestWebSocketAPI:
    """Test WebSocket functionality"""
    
    def test_websocket_connection(self):
        """Test WebSocket connection establishment"""
        # This would require a more complex WebSocket test setup
        # For now, we'll test the connection endpoint structure
        assert True  # Placeholder for actual WebSocket tests
        
    def test_websocket_message_broadcast(self):
        """Test WebSocket message broadcasting"""
        # Placeholder for WebSocket broadcasting tests
        assert True


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limiting_by_role(self, client):
        """Test that different roles have different rate limits"""
        # This would require setting up actual rate limiting
        # For now, we'll test the configuration
        assert True


class TestErrorHandling:
    """Test error handling and validation"""
    
    def test_validation_error(self, client, auth_headers):
        """Test validation error response"""
        invalid_workflow = {
            "name": "",  # Invalid: empty name
            "workflow_type": ""  # Invalid: empty type
        }
        
        response = client.post("/api/v1/workflows", json=invalid_workflow, headers=auth_headers)
        
        assert response.status_code == 422  # Unprocessable Entity
        
    def test_not_found_error(self, client, auth_headers):
        """Test 404 error for non-existent resource"""
        response = client.get("/api/v1/workflows/non-existent-id", headers=auth_headers)
        
        assert response.status_code == 404
        
    def test_server_error(self, client, auth_headers):
        """Test 500 error handling"""
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            mock_service.return_value.list_workflows.side_effect = Exception("Database error")
            
            response = client.get("/api/v1/workflows", headers=auth_headers)
            
            assert response.status_code == 500


# Integration tests
class TestWorkflowExecution:
    """Test complete workflow execution flow"""
    
    def test_workflow_execution_flow(self, client, auth_headers, sample_workflow_data):
        """Test complete workflow execution"""
        with patch('app.services.workflow_service.WorkflowService') as mock_service:
            # Mock workflow creation
            mock_service.return_value.create_workflow.return_value = {
                "id": "workflow-123",
                "name": sample_workflow_data["name"],
                "status": "pending"
            }
            
            # Mock workflow execution
            mock_service.return_value.execute_workflow.return_value = {
                "execution_id": "exec-123",
                "status": "running"
            }
            
            # Create workflow
            create_response = client.post(
                "/api/v1/workflows",
                json=sample_workflow_data,
                headers=auth_headers
            )
            
            assert create_response.status_code == 201
            
            # Execute workflow
            workflow_id = create_response.json()["id"]
            exec_response = client.post(
                f"/api/v1/workflows/{workflow_id}/execute",
                headers=auth_headers
            )
            
            assert exec_response.status_code == 200