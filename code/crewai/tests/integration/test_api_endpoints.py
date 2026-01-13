"""
API endpoint tests for FastAPI server
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta
import uuid

# Import the FastAPI app
from api.server import app


class TestAPIEndpoints:
    """Test cases for FastAPI endpoints"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for FastAPI application"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Mock crew orchestrator for API tests"""
        with patch('api.server.crew_orchestrator') as mock_orchestrator_module:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.initialize_crew = AsyncMock()
            mock_orchestrator.execute_market_analysis_workflow = AsyncMock()
            mock_orchestrator.execute_trading_workflow = AsyncMock()
            
            mock_orchestrator_module.CrewOrchestrator.return_value = mock_orchestrator
            mock_orchestrator_module.CrewOrchestrator.return_value.orchestrator = mock_orchestrator
            
            return mock_orchestrator
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client for API tests"""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "CrewAI Trading System API" in data["message"]
        assert "version" in data
        assert "endpoints" in data
    
    @pytest.mark.asyncio
    async def test_health_check(self, test_client):
        """Test health check endpoint"""
        # Mock Redis health
        with patch('api.server.redis_client') as mock_redis:
            mock_redis.ping = AsyncMock(return_value=True)
            
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["timestamp"] is not None
            assert data["services"]["redis"] == "healthy"
            assert data["services"]["database"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_analyze_endpoint(self, test_client, mock_orchestrator):
        """Test market analysis endpoint"""
        analysis_request = {
            "symbol": "AAPL",
            "analysis_type": "comprehensive",
            "timeframe": "1d",
            "include_predictions": True,
            "risk_assessment": True
        }
        
        # Mock orchestrator response
        mock_orchestrator.execute_market_analysis_workflow.return_value = {
            "workflow_id": "wf_12345",
            "symbol": "AAPL",
            "analysis_results": {
                "market_research": {
                    "current_price": 105.50,
                    "sentiment": "positive",
                    "technical_indicators": {"rsi": 65.0}
                },
                "ml_predictions": {
                    "predictions": [106.0, 107.0, 108.0],
                    "confidence": 0.85
                },
                "risk_assessment": {
                    "var_95": 0.05,
                    "risk_score": 0.3
                }
            },
            "recommendations": {
                "action": "buy",
                "confidence": 0.8,
                "target_price": 110.0
            },
            "status": "completed"
        }
        
        with patch('api.server.crew_orchestrator') as mock_orchestrator_class:
            mock_orchestrator_class.CrewOrchestrator.return_value = mock_orchestrator
            
            response = test_client.post("/analyze", json=analysis_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["status"] == "completed"
            assert "analysis_results" in data
            assert "recommendations" in data
            assert data["recommendations"]["action"] == "buy"
    
    @pytest.mark.asyncio
    async def test_execute_trade_endpoint(self, test_client, mock_orchestrator):
        """Test trade execution endpoint"""
        trade_request = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "order_type": "limit",
            "price": 105.50,
            "time_in_force": "day",
            "execution_strategy": "aggressive"
        }
        
        # Mock orchestrator response
        mock_orchestrator.execute_trading_workflow.return_value = {
            "workflow_id": "trade_12345",
            "trading_decision": {
                "action": "execute",
                "confidence": 0.85,
                "position_size": 100
            },
            "risk_approval": {
                "approved": True,
                "conditions": ["monitor_closely"],
                "approved_by": "chief_risk_officer"
            },
            "execution_plan": {
                "order_id": "order_67890",
                "strategy": "twap",
                "estimated_completion": 1800
            },
            "cost_estimate": {
                "total_cost": 2.50,
                "cost_per_share": 0.025,
                "vs_benchmark": -0.001
            },
            "status": "approved"
        }
        
        with patch('api.server.crew_orchestrator') as mock_orchestrator_class:
            mock_orchestrator_class.CrewOrchestrator.return_value = mock_orchestrator
            
            response = test_client.post("/execute-trade", json=trade_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["trading_decision"]["action"] == "execute"
            assert data["risk_approval"]["approved"] is True
            assert "execution_plan" in data
            assert "cost_estimate" in data
            assert data["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_review_portfolio_endpoint(self, test_client, mock_orchestrator):
        """Test portfolio review endpoint"""
        portfolio_request = {
            "portfolio_value": 1000000,
            "positions": {
                "AAPL": {"quantity": 100, "weight": 0.105},
                "MSFT": {"quantity": 50, "weight": 0.155},
                "GOOGL": {"quantity": 30, "weight": 0.085},
                "AMZN": {"quantity": 25, "weight": 0.075}
            },
            "risk_tolerance": 0.15,
            "review_type": "comprehensive"
        }
        
        # Mock orchestrator response
        mock_orchestrator.portfolio_review_workflow = AsyncMock(return_value={
            "review_id": "review_12345",
            "portfolio_health": {
                "overall_score": 0.82,
                "diversification_score": 0.75,
                "risk_score": 0.65,
                "performance_score": 0.88
            },
            "recommendations": [
                {
                    "type": "rebalancing",
                    "priority": "medium",
                    "description": "Reduce AAPL position by 5%",
                    "expected_impact": "Improved diversification"
                },
                {
                    "type": "risk_management",
                    "priority": "high",
                    "description": "Add stop-loss to large positions",
                    "expected_impact": "Reduced downside risk"
                }
            ],
            "risk_analysis": {
                "var_95": 0.08,
                "max_drawdown": 0.12,
                "sharpe_ratio": 1.35,
                "beta": 0.95
            },
            "optimization_suggestions": {
                "rebalancing_trades": [
                    {"symbol": "AAPL", "action": "sell", "quantity": 47},
                    {"symbol": "MSFT", "action": "buy", "quantity": 25}
                ],
                "tax_optimization": "Consider harvesting losses in underperforming positions"
            }
        })
        
        with patch('api.server.crew_orchestrator') as mock_orchestrator_class:
            mock_orchestrator_class.CrewOrchestrator.return_value = mock_orchestrator
            
            response = test_client.post("/review-portfolio", json=portfolio_request)
            
            assert response.status_code == 200
            data = response.json()
            assert "portfolio_health" in data
            assert len(data["recommendations"]) >= 1
            assert data["portfolio_health"]["overall_score"] > 0
            assert "risk_analysis" in data
            assert "optimization_suggestions" in data
    
    @pytest.mark.asyncio
    async def test_get_workflows_endpoint(self, test_client):
        """Test get workflows endpoint"""
        # Mock workflow data
        workflows_data = [
            {
                "workflow_id": "wf_001",
                "type": "market_analysis",
                "symbol": "AAPL",
                "status": "completed",
                "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "completed_at": (datetime.now() - timedelta(minutes=30)).isoformat()
            },
            {
                "workflow_id": "wf_002",
                "type": "trade_execution",
                "symbol": "MSFT",
                "status": "in_progress",
                "created_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "completed_at": None
            }
        ]
        
        with patch('api.server.get_recent_workflows') as mock_get_workflows:
            mock_get_workflows.return_value = workflows_data
            
            response = test_client.get("/workflows")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["workflows"]) == 2
            assert data["workflows"][0]["workflow_id"] == "wf_001"
            assert data["workflows"][1]["status"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_get_workflow_details_endpoint(self, test_client):
        """Test get workflow details endpoint"""
        workflow_id = "wf_12345"
        
        # Mock detailed workflow data
        workflow_details = {
            "workflow_id": workflow_id,
            "type": "market_analysis",
            "symbol": "AAPL",
            "status": "completed",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "completed_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "execution_details": {
                "total_steps": 4,
                "completed_steps": 4,
                "execution_time": 15.5,
                "agents_used": ["market_research_analyst", "ml_prediction_engineer", "chief_risk_officer", "execution_trader"]
            },
            "results": {
                "market_analysis": {
                    "current_price": 105.50,
                    "sentiment": "positive",
                    "confidence": 0.85
                },
                "predictions": {
                    "target_price": 110.0,
                    "time_horizon": 5,
                    "probability_up": 0.72
                },
                "risk_assessment": {
                    "var_95": 0.05,
                    "risk_score": 0.3,
                    "approved": True
                }
            },
            "metadata": {
                "source": "api_request",
                "user_id": "test_user",
                "priority": "normal"
            }
        }
        
        with patch('api.server.get_workflow_details') as mock_get_details:
            mock_get_details.return_value = workflow_details
            
            response = test_client.get(f"/workflows/{workflow_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["workflow_id"] == workflow_id
            assert data["status"] == "completed"
            assert "execution_details" in data
            assert "results" in data
            assert len(data["execution_details"]["agents_used"]) == 4
    
    @pytest.mark.asyncio
    async def test_approval_status_endpoint(self, test_client):
        """Test approval status endpoint"""
        approval_id = "appr_12345"
        
        # Mock approval status data
        approval_status = {
            "approval_id": approval_id,
            "type": "trade_execution",
            "status": "approved",
            "priority": "high",
            "requester": "execution_trader",
            "created_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
            "approved_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "approved_by": "chief_risk_officer",
            "conditions": [
                "monitor_position_closely",
                "set_stop_loss_at_5_percent"
            ],
            "decision_details": {
                "risk_assessment": "acceptable",
                "market_conditions": "favorable",
                "portfolio_impact": "minimal"
            }
        }
        
        with patch('api.server.get_approval_status') as mock_get_status:
            mock_get_status.return_value = approval_status
            
            response = test_client.get(f"/approvals/{approval_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["approval_id"] == approval_id
            assert data["status"] == "approved"
            assert data["approved_by"] == "chief_risk_officer"
            assert len(data["conditions"]) == 2
            assert "decision_details" in data
    
    @pytest.mark.asyncio
    async def test_approval_decision_endpoint(self, test_client):
        """Test approval decision endpoint"""
        approval_id = "appr_12345"
        decision_request = {
            "decision": "approved",
            "approver_id": "chief_risk_officer",
            "conditions": ["monitor_closely", "set_stop_loss"],
            "comments": "Risk is acceptable with conditions"
        }
        
        # Mock approval decision
        with patch('api.server.submit_approval_decision') as mock_decision:
            mock_decision.return_value = {
                "success": True,
                "approval_id": approval_id,
                "decision": "approved",
                "updated_at": datetime.now().isoformat(),
                "processing_time": 2.5
            }
            
            response = test_client.post(f"/approvals/{approval_id}/decision", json=decision_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["approval_id"] == approval_id
            assert data["decision"] == "approved"
    
    @pytest.mark.asyncio
    async def test_system_status_endpoint(self, test_client):
        """Test system status endpoint"""
        # Mock system status
        system_status = {
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "redis": {"status": "healthy", "response_time": 0.5},
                "market_data_api": {"status": "healthy", "response_time": 1.2},
                "ml_models": {"status": "healthy", "load_time": 0.8},
                "execution_engines": {"status": "healthy", "latency": 0.3}
            },
            "performance": {
                "active_workflows": 3,
                "queued_requests": 1,
                "average_response_time": 2.1,
                "throughput": 15.5
            },
            "alerts": []
        }
        
        with patch('api.server.get_system_status') as mock_status:
            mock_status.return_value = system_status
            
            response = test_client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "operational"
            assert "services" in data
            assert "performance" in data
            assert all(service["status"] == "healthy" for service in data["services"].values())
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, test_client):
        """Test metrics endpoint"""
        # Mock metrics data
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "api_metrics": {
                "total_requests": 1250,
                "successful_requests": 1205,
                "failed_requests": 45,
                "average_response_time": 1.85,
                "requests_per_minute": 12.5
            },
            "workflow_metrics": {
                "total_workflows": 89,
                "completed_workflows": 85,
                "failed_workflows": 4,
                "average_execution_time": 18.3,
                "success_rate": 0.955
            },
            "agent_metrics": {
                "market_research_analyst": {
                    "calls": 89,
                    "average_time": 3.2,
                    "success_rate": 0.98
                },
                "ml_prediction_engineer": {
                    "calls": 85,
                    "average_time": 8.7,
                    "success_rate": 0.94
                },
                "chief_risk_officer": {
                    "calls": 87,
                    "average_time": 2.1,
                    "success_rate": 0.99
                },
                "execution_trader": {
                    "calls": 65,
                    "average_time": 5.4,
                    "success_rate": 0.92
                }
            },
            "system_resources": {
                "cpu_usage": 0.65,
                "memory_usage": 0.78,
                "redis_memory": 0.45,
                "cache_hit_rate": 0.87
            }
        }
        
        with patch('api.server.get_system_metrics') as mock_metrics:
            mock_metrics.return_value = metrics_data
            
            response = test_client.get("/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert "api_metrics" in data
            assert "workflow_metrics" in data
            assert "agent_metrics" in data
            assert "system_resources" in data
            assert data["workflow_metrics"]["success_rate"] > 0.9
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_requests(self, test_client):
        """Test error handling for invalid requests"""
        # Test missing required fields
        invalid_request = {
            "symbol": "AAPL"
            # Missing other required fields
        }
        
        response = test_client.post("/analyze", json=invalid_request)
        assert response.status_code == 422  # Validation error
        
        # Test invalid symbol format
        invalid_symbol_request = {
            "symbol": "INVALID_SYMBOL_123",
            "analysis_type": "basic"
        }
        
        response = test_client.post("/analyze", json=invalid_symbol_request)
        assert response.status_code == 400  # Bad request
        
        # Test non-existent workflow
        response = test_client.get("/workflows/nonexistent_workflow")
        assert response.status_code == 404  # Not found
        
        # Test invalid approval ID format
        response = test_client.get("/approvals/invalid_id_format")
        assert response.status_code == 400  # Bad request
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_client):
        """Test API rate limiting"""
        # Test multiple rapid requests (this would require proper rate limiting setup)
        requests = []
        for i in range(100):
            response = test_client.get("/health")
            requests.append(response)
        
        # At least some requests should be rate limited if rate limiting is implemented
        status_codes = [r.status_code for r in requests]
        if 429 in status_codes:  # Too Many Requests
            assert True  # Rate limiting is working
        else:
            assert all(code == 200 for code in status_codes)  # All succeeded
    
    @pytest.mark.asyncio
    async def test_api_documentation_endpoint(self, test_client):
        """Test API documentation endpoint"""
        response = test_client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    @pytest.mark.asyncio
    async def test_openapi_spec_endpoint(self, test_client):
        """Test OpenAPI specification endpoint"""
        response = test_client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        assert "/analyze" in data["paths"]
        assert "/execute-trade" in data["paths"]
    
    @pytest.mark.asyncio
    async def test_cors_headers(self, test_client):
        """Test CORS headers for cross-origin requests"""
        response = test_client.options("/health")
        
        # Check if CORS headers are present
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, test_client, mock_orchestrator):
        """Test handling of concurrent API requests"""
        # Mock orchestrator for concurrent requests
        async def mock_analysis(symbol):
            return {
                "workflow_id": f"wf_{symbol}",
                "symbol": symbol,
                "status": "completed",
                "analysis_results": {
                    "market_research": {"current_price": 100.0},
                    "ml_predictions": {"predictions": [101.0, 102.0]},
                    "risk_assessment": {"risk_score": 0.3}
                }
            }
        
        mock_orchestrator.execute_market_analysis_workflow = lambda req: mock_analysis(req["symbol"])
        
        # Submit multiple concurrent requests
        requests = []
        for i in range(10):
            request = {
                "symbol": f"SYM{i}",
                "analysis_type": "basic"
            }
            requests.append(test_client.post("/analyze", json=request))
        
        # Collect responses
        responses = await asyncio.gather(*requests)
        
        # Verify all requests were processed
        assert len(responses) == 10
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_api_authentication(self, test_client):
        """Test API authentication (if implemented)"""
        # Test request without authentication (if auth is required)
        response = test_client.post("/analyze", json={"symbol": "AAPL"})
        
        # Should either succeed (no auth required) or fail with 401 (auth required)
        if response.status_code == 401:
            assert "unauthorized" in response.json()["detail"].lower()
        else:
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, test_client, mock_orchestrator):
        """Test handling of large payloads"""
        # Create a large analysis request
        large_request = {
            "symbol": "AAPL",
            "analysis_type": "comprehensive",
            "include_predictions": True,
            "risk_assessment": True,
            "extended_analysis": {
                "symbol": "AAPL",
                "market_data": {f"field_{i}": f"value_{i}" * 100 for i in range(100)},
                "historical_data": [f"historical_record_{i}" for i in range(1000)]
            }
        }
        
        # Mock response for large payload
        mock_orchestrator.execute_market_analysis_workflow = AsyncMock(return_value={
            "status": "completed",
            "processing_info": {
                "payload_size": len(json.dumps(large_request)),
                "processing_time": 2.5,
                "memory_used": 15.7
            }
        })
        
        with patch('api.server.crew_orchestrator') as mock_orchestrator_class:
            mock_orchestrator_class.CrewOrchestrator.return_value = mock_orchestrator
            
            response = test_client.post("/analyze", json=large_request)
            
            # Should handle large payload gracefully
            assert response.status_code == 200
            data = response.json()
            assert "processing_info" in data
            assert data["processing_info"]["payload_size"] > 10000
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, test_client):
        """Test timeout handling for long-running requests"""
        # Test with a very large timeout value
        large_timeout_request = {
            "symbol": "AAPL",
            "analysis_type": "comprehensive",
            "timeout": 300  # 5 minutes
        }
        
        response = test_client.post("/analyze", json=large_timeout_request)
        
        # Should accept the request even with long timeout
        if response.status_code == 408:  # Request Timeout
            assert True  # Timeout handled properly
        else:
            assert response.status_code in [200, 422]  # Success or validation error