"""
Integration tests for Approval Workflow
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta
import uuid

# Import the approval workflow
from orchestration.approval_workflow import ApprovalWorkflow, TradeApprovalWorkflow


class TestApprovalWorkflow:
    """Test cases for Approval Workflow"""
    
    @pytest.fixture
    def approval_workflow(self, mock_redis_client):
        """Create ApprovalWorkflow instance with mocked dependencies"""
        with patch('orchestration.approval_workflow.redis.from_url') as mock_from_url, \
             patch('orchestration.approval_workflow.ApprovalWorkflow._setup_redis') as mock_setup:
            
            mock_from_url.return_value = mock_redis_client
            mock_setup.return_value = mock_redis_client
            
            workflow = ApprovalWorkflow(
                redis_url="redis://localhost:6379/2",
                approval_config={
                    'high_risk_threshold': 0.8,
                    'medium_risk_threshold': 0.5,
                    'high_value_threshold': 10000.0,
                    'approval_timeout': 3600  # 1 hour
                }
            )
            
            workflow.redis_client = mock_redis_client
            return workflow
    
    @pytest.mark.asyncio
    async def test_initialization(self, approval_workflow):
        """Test approval workflow initialization"""
        assert approval_workflow.redis_url == "redis://localhost:6379/2"
        assert approval_workflow.approval_config['high_risk_threshold'] == 0.8
        assert approval_workflow.approval_config['high_value_threshold'] == 10000.0
        
        # Test Redis connection
        await approval_workflow.redis_client.ping()
        assert True
    
    @pytest.mark.asyncio
    async def test_submit_approval_request(self, approval_workflow, sample_approval_request):
        """Test submitting an approval request"""
        request = {
            'approval_id': 'appr_test_001',
            'request_id': 'req_test_001',
            'type': 'trade_execution',
            'priority': 'high',
            'requester': 'execution_trader',
            'details': {
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 1000,
                'estimated_value': 105000.0,
                'risk_score': 0.85,
                'reason': 'High confidence ML signal'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Mock Redis operations
        approval_workflow.redis_client.hset = AsyncMock(return_value=1)
        approval_workflow.redis_client.lpush = AsyncMock(return_value=1)
        
        result = await approval_workflow.submit_approval_request(request)
        
        # Verify submission
        assert result['success'] is True
        assert result['approval_id'] is not None
        assert result['status'] == 'pending'
        assert result['queue_position'] > 0
        
        # Verify Redis was called correctly
        approval_workflow.redis_client.hset.assert_called_once()
        approval_workflow.redis_client.lpush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_approval_status(self, approval_workflow):
        """Test checking approval request status"""
        approval_id = 'appr_test_001'
        
        # Mock stored approval data
        stored_data = {
            'approval_id': approval_id,
            'status': 'approved',
            'priority': 'high',
            'requester': 'execution_trader',
            'created_at': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'approved_at': (datetime.now() - timedelta(minutes=10)).isoformat(),
            'approved_by': 'risk_officer',
            'conditions': ['reduce_position_size', 'add_stop_loss']
        }
        
        approval_workflow.redis_client.hgetall.return_value = stored_data
        
        result = await approval_workflow.check_approval_status(approval_id)
        
        # Verify status check
        assert result['success'] is True
        assert result['approval_id'] == approval_id
        assert result['status'] == 'approved'
        assert result['approved_by'] == 'risk_officer'
        assert len(result['conditions']) == 2
        assert result['processing_time'] is not None
    
    @pytest.mark.asyncio
    async def test_approve_request(self, approval_workflow, sample_approval_request):
        """Test approving an approval request"""
        approval_id = 'appr_test_001'
        approver_id = 'chief_risk_officer'
        approval_data = {
            'decision': 'approved',
            'conditions': ['reduce_position_to_80_percent', 'monitor_closely'],
            'comments': 'Risk is acceptable with conditions',
            'approved_by': approver_id
        }
        
        # Mock Redis get and set operations
        approval_workflow.redis_client.hgetall.return_value = {
            'approval_id': approval_id,
            'status': 'pending',
            'type': 'trade_execution',
            'priority': 'high'
        }
        
        approval_workflow.redis_client.hset = AsyncMock(return_value=1)
        approval_workflow.redis_client.lrem = AsyncMock(return_value=1)
        approval_workflow.redis_client.lpush = AsyncMock(return_value=1)
        
        result = await approval_workflow.approve_request(approval_id, approval_data)
        
        # Verify approval
        assert result['success'] is True
        assert result['approval_id'] == approval_id
        assert result['decision'] == 'approved'
        assert result['approved_by'] == approver_id
        assert result['conditions'] == ['reduce_position_to_80_percent', 'monitor_closely']
        
        # Verify status transition
        final_status = await approval_workflow.check_approval_status(approval_id)
        assert final_status['status'] == 'approved'
    
    @pytest.mark.asyncio
    async def test_reject_request(self, approval_workflow, sample_approval_request):
        """Test rejecting an approval request"""
        approval_id = 'appr_test_002'
        approver_id = 'risk_officer'
        rejection_data = {
            'decision': 'rejected',
            'reason': 'Risk score exceeds acceptable threshold',
            'comments': 'Position size too large relative to portfolio',
            'rejected_by': approver_id
        }
        
        # Mock Redis operations
        approval_workflow.redis_client.hgetall.return_value = {
            'approval_id': approval_id,
            'status': 'pending',
            'type': 'trade_execution',
            'priority': 'medium'
        }
        
        approval_workflow.redis_client.hset = AsyncMock(return_value=1)
        approval_workflow.redis_client.lrem = AsyncMock(return_value=1)
        
        result = await approval_workflow.reject_request(approval_id, rejection_data)
        
        # Verify rejection
        assert result['success'] is True
        assert result['approval_id'] == approval_id
        assert result['decision'] == 'rejected'
        assert result['rejected_by'] == approver_id
        assert 'risk score exceeds' in result['reason'].lower()
        
        # Verify status transition
        final_status = await approval_workflow.check_approval_status(approval_id)
        assert final_status['status'] == 'rejected'
    
    @pytest.mark.asyncio
    async def test_auto_approval_logic(self, approval_workflow):
        """Test automatic approval for low-risk requests"""
        auto_approval_request = {
            'type': 'trade_execution',
            'details': {
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 100,
                'estimated_value': 10500.0,  # Below threshold
                'risk_score': 0.3  # Below medium threshold
            }
        }
        
        # Mock low-risk detection
        with patch.object(approval_workflow, '_is_auto_approvable') as mock_auto_approve:
            mock_auto_approve.return_value = True
            
            result = await approval_workflow.auto_approval_logic(auto_approval_request)
            
            assert result['auto_approved'] is True
            assert result['reason'] == 'low_risk_request'
            assert result['approval_id'] is not None
            assert result['processing_time'] < 1.0  # Should be very fast
    
    @pytest.mark.asyncio
    async def test_batch_approval_processing(self, approval_workflow):
        """Test processing multiple approval requests in batch"""
        batch_requests = [
            {
                'approval_id': 'appr_batch_001',
                'type': 'position_sizing',
                'priority': 'high',
                'details': {'symbol': 'AAPL', 'risk_score': 0.85}
            },
            {
                'approval_id': 'appr_batch_002',
                'type': 'portfolio_rebalance',
                'priority': 'medium',
                'details': {'rebalance_ratio': 0.05}
            },
            {
                'approval_id': 'appr_batch_003',
                'type': 'model_update',
                'priority': 'low',
                'details': {'model_version': 'v2.1'}
            }
        ]
        
        # Mock Redis operations for batch processing
        approval_workflow.redis_client.hset = AsyncMock(return_value=1)
        approval_workflow.redis_client.lpush = AsyncMock(return_value=1)
        
        results = await asyncio.gather(*[
            approval_workflow.submit_approval_request(req) for req in batch_requests
        ])
        
        # Verify all requests were processed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result['success'] is True
            assert result['approval_id'] == batch_requests[i]['approval_id']
            assert result['batch_position'] == i + 1
    
    @pytest.mark.asyncio
    async def test_approval_workflow_escalation(self, approval_workflow):
        """Test escalation logic for overdue approvals"""
        escalation_request = {
            'approval_id': 'appr_escalate_001',
            'type': 'emergency_trade',
            'priority': 'critical',
            'created_at': (datetime.now() - timedelta(hours=2)).isoformat(),
            'current_approver': 'junior_analyst',
            'overdue': True
        }
        
        # Mock escalation trigger
        with patch.object(approval_workflow, '_should_escalate') as mock_escalate:
            mock_escalate.return_value = True
            
            result = await approval_workflow.handle_escalation(escalation_request)
            
            assert result['escalated'] is True
            assert result['new_approver'] in ['senior_risk_officer', 'chief_risk_officer']
            assert 'timeout_reason' in result
            assert result['urgency_level'] == 'critical'
    
    @pytest.mark.asyncio
    async def test_approval_queue_management(self, approval_workflow):
        """Test approval queue prioritization and management"""
        # Create mixed priority requests
        requests = [
            {'priority': 'critical', 'created_at': datetime.now() - timedelta(minutes=1)},
            {'priority': 'high', 'created_at': datetime.now() - timedelta(minutes=2)},
            {'priority': 'medium', 'created_at': datetime.now() - timedelta(minutes=3)},
            {'priority': 'low', 'created_at': datetime.now() - timedelta(minutes=1)}  # Recent low priority
        ]
        
        # Mock queue data
        queue_data = [
            json.dumps({'approval_id': f'appr_{i}', 'priority': req['priority']}) 
            for i, req in enumerate(requests)
        ]
        
        approval_workflow.redis_client.lrange.return_value = queue_data
        approval_workflow.redis_client.ltrim = AsyncMock(return_value=True)
        
        result = await approval_workflow.get_approval_queue()
        
        # Verify queue management
        assert result['success'] is True
        assert len(result['queue']) == 4
        
        # Verify priority ordering (critical first, then by time)
        priorities = [item['priority'] for item in result['queue']]
        assert priorities[0] == 'critical'
        assert 'high' in priorities
        
        # Verify queue statistics
        assert result['queue_stats']['total_requests'] == 4
        assert result['queue_stats']['by_priority']['critical'] == 1
        assert result['queue_stats']['average_wait_time'] > 0
    
    @pytest.mark.asyncio
    async def test_approval_workflow_monitoring(self, approval_workflow):
        """Test approval workflow monitoring and metrics"""
        # Mock workflow metrics
        metrics_data = {
            'total_requests': 150,
            'approved_count': 120,
            'rejected_count': 20,
            'auto_approved_count': 10,
            'average_processing_time': 15.5,  # minutes
            'overdue_requests': 5,
            'escalation_count': 3
        }
        
        approval_workflow.redis_client.get.return_value = json.dumps(metrics_data)
        
        result = await approval_workflow.get_workflow_metrics()
        
        # Verify metrics
        assert result['success'] is True
        assert result['metrics'] == metrics_data
        assert result['approval_rate'] == 120 / 150
        assert result['auto_approval_rate'] == 10 / 150
        assert result['overdue_rate'] == 5 / 150
        
        # Verify performance indicators
        assert result['performance_indicators']['processing_speed'] == 'fast'  # < 30 minutes average
        assert result['performance_indicators']['approval_efficiency'] == 'high'  # > 80% approval rate
    
    @pytest.mark.asyncio
    async def test_approval_workflow_integration_with_risk(self, approval_workflow):
        """Test integration with risk management systems"""
        high_risk_request = {
            'type': 'large_position_trade',
            'details': {
                'symbol': 'TSLA',
                'side': 'buy',
                'quantity': 5000,
                'estimated_value': 1500000.0,  # Very high value
                'risk_score': 0.95,  # Very high risk
                'portfolio_impact': 0.25
            }
        }
        
        # Mock risk integration
        with patch.object(approval_workflow, '_integrate_with_risk_system') as mock_risk:
            mock_risk.return_value = {
                'risk_approval_required': True,
                'risk_level': 'extreme',
                'required_approvers': ['chief_risk_officer', 'portfolio_manager'],
                'additional_conditions': [
                    'reduce_position_size',
                    'implement_hedging_strategy',
                    'increase_monitoring_frequency'
                ]
            }
            
            result = await approval_workflow.integrate_with_risk_assessment(high_risk_request)
            
            # Verify risk integration
            assert result['risk_approval_required'] is True
            assert result['risk_level'] == 'extreme'
            assert len(result['required_approvers']) >= 2
            assert len(result['additional_conditions']) >= 2
            
            # Verify it escalates to higher approval requirements
            assert result['approval_requirements']['risk_review'] is True
            assert result['approval_requirements']['documentation_required'] is True
    
    @pytest.mark.asyncio
    async def test_approval_workflow_auditing(self, approval_workflow):
        """Test approval workflow auditing and compliance"""
        # Create test approval with full audit trail
        audit_request = {
            'approval_id': 'appr_audit_001',
            'requester': 'execution_trader',
            'type': 'trade_execution',
            'details': {
                'symbol': 'AAPL',
                'value': 50000.0,
                'risk_score': 0.7
            },
            'audit_info': {
                'request_source': 'api',
                'user_agent': 'trading_system',
                'ip_address': '192.168.1.100',
                'session_id': 'sess_abc123'
            }
        }
        
        # Mock audit trail operations
        approval_workflow.redis_client.lpush = AsyncMock(return_value=1)
        approval_workflow.redis_client.sadd = AsyncMock(return_value=1)
        
        result = await approval_workflow.log_audit_trail(audit_request)
        
        # Verify audit logging
        assert result['success'] is True
        assert result['audit_id'] is not None
        assert result['compliance_check'] == 'passed'
        
        # Verify audit data integrity
        audit_data = await approval_workflow.get_audit_trail('appr_audit_001')
        assert audit_data['source_ip'] == '192.168.1.100'
        assert audit_data['session_tracked'] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_approval_processing(self, approval_workflow):
        """Test concurrent approval request processing"""
        concurrent_requests = []
        
        for i in range(10):
            request = {
                'approval_id': f'appr_concurrent_{i}',
                'type': 'trade_execution',
                'priority': 'medium',
                'details': {
                    'symbol': f'SYM_{i}',
                    'value': 10000.0 + i * 1000,
                    'risk_score': 0.4 + i * 0.05
                }
            }
            concurrent_requests.append(request)
        
        # Process requests concurrently
        results = await asyncio.gather(*[
            approval_workflow.submit_approval_request(req) 
            for req in concurrent_requests
        ])
        
        # Verify all concurrent requests were processed
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result['success'] is True
            assert result['approval_id'] == f'appr_concurrent_{i}'
            assert result['processing_time'] < 1.0  # Should be fast
    
    @pytest.mark.asyncio
    async def test_approval_workflow_error_handling(self, approval_workflow):
        """Test error handling in approval workflow"""
        # Test with invalid request
        invalid_request = {
            'approval_id': '',  # Empty ID
            'type': '',  # Empty type
            'details': None  # Missing details
        }
        
        result = await approval_workflow.submit_approval_request(invalid_request)
        
        assert result['success'] is False
        assert 'invalid_request' in result['error'].lower()
        
        # Test with Redis failure
        approval_workflow.redis_client.hset = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        valid_request = {
            'approval_id': 'appr_error_001',
            'type': 'trade_execution',
            'details': {'symbol': 'AAPL', 'value': 1000}
        }
        
        result = await approval_workflow.submit_approval_request(valid_request)
        
        assert result['success'] is False
        assert 'redis' in result['error'].lower()
        
        # Test with timeout
        approval_workflow.approval_config['approval_timeout'] = 1  # 1 second timeout
        
        timeout_request = {
            'approval_id': 'appr_timeout_001',
            'type': 'slow_processing',
            'details': {'complexity': 'very_high'}
        }
        
        # Mock long processing time
        approval_workflow.redis_client.hset = AsyncMock(side_effect=asyncio.TimeoutError())
        
        result = await approval_workflow.submit_approval_request(timeout_request)
        
        assert result['success'] is False
        assert 'timeout' in result['error'].lower()


class TestTradeApprovalWorkflow:
    """Test cases for Trade-specific Approval Workflow"""
    
    @pytest.fixture
    def trade_approval_workflow(self, mock_redis_client):
        """Create TradeApprovalWorkflow instance"""
        with patch('orchestration.approval_workflow.TradeApprovalWorkflow._setup_redis') as mock_setup:
            mock_setup.return_value = mock_redis_client
            
            workflow = TradeApprovalWorkflow(redis_client=mock_redis_client)
            workflow.redis_client = mock_redis_client
            return workflow
    
    @pytest.mark.asyncio
    async def test_trade_risk_assessment(self, trade_approval_workflow, sample_trade_data):
        """Test trade-specific risk assessment"""
        trade_request = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 1000,
            'price': 105.50,
            'order_type': 'limit',
            'portfolio_context': {
                'total_value': 1000000,
                'current_positions': {
                    'AAPL': {'quantity': 500, 'weight': 0.0525},
                    'MSFT': {'quantity': 300, 'weight': 0.093}
                },
                'risk_tolerance': 0.15
            }
        }
        
        result = await trade_approval_workflow.assess_trade_risk(trade_request)
        
        # Verify risk assessment
        assert 'risk_score' in result
        assert 'risk_factors' in result
        assert 'position_impact' in result
        assert 'portfolio_risk' in result
        
        # Verify risk score calculation
        assert 0 <= result['risk_score'] <= 1
        assert isinstance(result['risk_factors'], list)
        assert result['position_impact']['new_weight'] > 0
    
    @pytest.mark.asyncio
    async def test_position_sizing_approval(self, trade_approval_workflow):
        """Test position sizing approval logic"""
        position_request = {
            'symbol': 'TSLA',
            'current_position': 0,
            'proposed_position': 2000,
            'proposed_value': 400000,
            'portfolio_value': 2000000,
            'risk_metrics': {
                'var_95': 0.08,
                'sharpe_ratio': 1.2,
                'max_drawdown': 0.15
            }
        }
        
        result = await trade_approval_workflow.evaluate_position_size(position_request)
        
        # Verify position evaluation
        assert 'approval_recommendation' in result
        assert 'position_adjustments' in result
        assert 'risk_assessment' in result
        
        # Verify recommendation types
        assert result['approval_recommendation'] in ['approve', 'adjust', 'reject']
        
        if result['approval_recommendation'] == 'adjust':
            assert 'adjusted_size' in result['position_adjustments']
            assert 'justification' in result['position_adjustments']
    
    @pytest.mark.asyncio
    async def test_emergency_trade_protocol(self, trade_approval_workflow):
        """Test emergency trade approval protocol"""
        emergency_trade = {
            'emergency_type': 'stop_loss_trigger',
            'symbol': 'AAPL',
            'action': 'sell',
            'quantity': 1000,
            'reason': 'stop_loss_triggered',
            'urgency': 'immediate',
            'market_conditions': 'volatile'
        }
        
        result = await trade_approval_workflow.process_emergency_trade(emergency_trade)
        
        # Verify emergency processing
        assert result['processed_immediately'] is True
        assert result['emergency_protocol'] == 'activated'
        assert result['approval_status'] in ['auto_approved', 'conditional_approved']
        
        # Verify emergency flags
        assert result['audit_trail']['emergency_flag'] is True
        assert result['audit_trail']['urgency_level'] == 'immediate'
        assert 'timestamp' in result['audit_trail']
    
    @pytest.mark.asyncio
    async def test_portfolio_impact_assessment(self, trade_approval_workflow):
        """Test portfolio impact assessment for trades"""
        portfolio_trade = {
            'trade_details': {
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 500,
                'price': 105.50
            },
            'current_portfolio': {
                'total_value': 1000000,
                'positions': {
                    'AAPL': {'quantity': 200, 'value': 20000, 'weight': 0.02},
                    'MSFT': {'quantity': 300, 'value': 90000, 'weight': 0.09},
                    'GOOGL': {'quantity': 100, 'value': 125000, 'weight': 0.125}
                },
                'sector_allocation': {
                    'Technology': 0.235,
                    'Healthcare': 0.15,
                    'Finance': 0.10
                }
            },
            'target_portfolio': {
                'target_weights': {
                    'AAPL': 0.025,
                    'MSFT': 0.08,
                    'GOOGL': 0.12
                }
            }
        }
        
        result = await trade_approval_workflow.assess_portfolio_impact(portfolio_trade)
        
        # Verify impact assessment
        assert 'current_vs_target' in result
        assert 'sector_impact' in result
        assert 'rebalancing_needed' in result
        assert 'risk_adjustments' in result
        
        # Verify portfolio calculations
        current_tech = result['current_vs_target']['technology_exposure']['current']
        target_tech = result['current_vs_target']['technology_exposure']['target']
        assert current_tech >= 0
        assert target_tech >= 0
        assert abs(current_tech - target_tech) <= 0.1  # Small difference expected
        
        # Verify rebalancing recommendation
        if result['rebalancing_needed']:
            assert 'rebalancing_trades' in result
            assert isinstance(result['rebalancing_trades'], list)


class TestApprovalWorkflowIntegration:
    """Integration tests for approval workflow components"""
    
    @pytest.mark.asyncio
    async def test_full_approval_workflow(self):
        """Test complete approval workflow from request to resolution"""
        pass  # Would test end-to-end approval process
    
    @pytest.mark.asyncio
    async def test_approval_workflow_with_orchestrator(self):
        """Test integration between approval workflow and orchestrator"""
        pass  # Would test crew orchestrator calling approval workflow