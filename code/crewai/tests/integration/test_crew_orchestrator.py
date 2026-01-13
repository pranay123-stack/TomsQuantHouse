"""
Integration tests for Crew Orchestrator
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Import the orchestrator
from orchestration.crew_orchestrator import CrewOrchestrator
from config.settings import TradingSettings


class TestCrewOrchestrator:
    """Test cases for Crew Orchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create CrewOrchestrator instance"""
        return CrewOrchestrator()
    
    @pytest.fixture
    def mock_crew(self, orchestrator):
        """Mock the crew setup"""
        with patch.object(orchestrator, '_initialize_agents') as mock_init_agents, \
             patch.object(orchestrator, '_setup_memory') as mock_setup_memory:
            
            # Mock agent initialization
            mock_agent = Mock()
            mock_agent.name = "Test Agent"
            mock_agent.role = "Test Role"
            mock_agent.run = AsyncMock()
            
            orchestrator.agents = {
                'market_research_analyst': mock_agent,
                'ml_prediction_engineer': mock_agent,
                'chief_risk_officer': mock_agent,
                'execution_trader': mock_agent
            }
            
            # Mock crew kickoff
            orchestrator.crew = Mock()
            orchestrator.crew.kickoff = AsyncMock(return_value="Mock Crew Result")
            
            yield orchestrator
    
    @pytest.fixture
    def sample_workflow_data(self):
        """Sample data for workflow testing"""
        return {
            'symbol': 'AAPL',
            'analysis_requirements': {
                'timeframe': '1d',
                'include_ml_predictions': True,
                'risk_assessment': True,
                'execution_plan': True
            },
            'constraints': {
                'max_position_size': 1000,
                'risk_tolerance': 0.05,
                'execution_strategy': 'twap'
            }
        }
    
    @pytest.mark.asyncio
    async def test_initialize_crew(self, orchestrator):
        """Test crew initialization"""
        with patch('agents.market_research_analyst.MarketResearchAnalyst') as mock_market_agent, \
             patch('agents.ml_prediction_engineer.MLPredictionEngineer') as mock_ml_agent, \
             patch('agents.chief_risk_officer.ChiefRiskOfficer') as mock_risk_agent, \
             patch('agents.execution_trader.ExecutionTrader') as mock_exec_agent:
            
            # Mock agent creation
            mock_market_agent.return_value = Mock(name="Market Research Analyst")
            mock_ml_agent.return_value = Mock(name="ML Prediction Engineer")
            mock_risk_agent.return_value = Mock(name="Chief Risk Officer")
            mock_exec_agent.return_value = Mock(name="Execution Trader")
            
            # Mock crew creation
            with patch('crewai.Crew') as mock_crew_class:
                mock_crew = Mock()
                mock_crew_class.return_value = mock_crew
                
                await orchestrator.initialize_crew()
                
                # Verify agents were created
                assert len(orchestrator.agents) == 4
                assert 'market_research_analyst' in orchestrator.agents
                assert 'ml_prediction_engineer' in orchestrator.agents
                assert 'chief_risk_officer' in orchestrator.agents
                assert 'execution_trader' in orchestrator.agents
    
    @pytest.mark.asyncio
    async def test_execute_market_analysis_workflow(self, orchestrator, mock_crew, sample_workflow_data):
        """Test complete market analysis workflow"""
        # Mock agent responses
        orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
            'market_data': {'current_price': 105.0, 'volume': 1000000},
            'sentiment': 'positive',
            'technical_indicators': {'rsi': 65.0}
        })
        
        orchestrator.agents['ml_prediction_engineer'].run = AsyncMock(return_value={
            'predictions': [106.0, 107.0, 108.0],
            'confidence': 0.85,
            'model_metrics': {'accuracy': 0.87}
        })
        
        orchestrator.agents['chief_risk_officer'].run = AsyncMock(return_value={
            'risk_assessment': {'var_95': 0.05, 'risk_score': 0.3},
            'compliance_status': 'passed'
        })
        
        orchestrator.agents['execution_trader'].run = AsyncMock(return_value={
            'execution_plan': {'strategy': 'twap', 'position_size': 500},
            'signal': {'action': 'buy', 'strength': 0.7}
        })
        
        result = await orchestrator.execute_market_analysis_workflow(sample_workflow_data)
        
        # Verify workflow structure
        assert 'workflow_id' in result
        assert 'symbol' in result
        assert 'analysis_results' in result
        assert 'recommendations' in result
        assert 'execution_plan' in result
        
        # Verify all agents contributed
        assert 'market_research' in result['analysis_results']
        assert 'ml_predictions' in result['analysis_results']
        assert 'risk_assessment' in result['analysis_results']
        
        # Verify workflow completion
        assert result['status'] == 'completed'
        assert result['symbol'] == sample_workflow_data['symbol']
    
    @pytest.mark.asyncio
    async def test_execute_trading_workflow(self, orchestrator, mock_crew):
        """Test trading workflow execution"""
        trading_request = {
            'action': 'analyze_and_execute',
            'symbol': 'MSFT',
            'strategy': 'momentum',
            'risk_parameters': {
                'max_risk': 0.03,
                'stop_loss': 0.05,
                'take_profit': 0.15
            },
            'execution_preferences': {
                'urgency': 'normal',
                'venue_preference': 'auto'
            }
        }
        
        # Mock agent responses for trading workflow
        orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
            'market_analysis': {
                'trend': 'bullish',
                'support_level': 295.0,
                'resistance_level': 310.0
            },
            'sentiment_score': 0.75
        })
        
        orchestrator.agents['ml_prediction_engineer'].run = AsyncMock(return_value={
            'price_prediction': 315.0,
            'confidence': 0.82,
            'time_horizon': 5
        })
        
        orchestrator.agents['chief_risk_officer'].run = AsyncMock(return_value={
            'risk_metrics': {
                'var_95': 0.04,
                'position_risk': 0.025,
                'portfolio_impact': 0.01
            },
            'risk_approval': 'approved',
            'max_position_size': 300
        })
        
        orchestrator.agents['execution_trader'].run = AsyncMock(return_value={
            'execution_details': {
                'order_id': 'order_12345',
                'execution_strategy': 'twap',
                'estimated_completion': 1800  # 30 minutes
            },
            'cost_analysis': {
                'total_cost': 3.5,
                'cost_per_share': 0.012,
                'vs_benchmark': -0.002
            }
        })
        
        result = await orchestrator.execute_trading_workflow(trading_request)
        
        # Verify trading workflow structure
        assert 'trading_decision' in result
        assert 'risk_approval' in result
        assert 'execution_plan' in result
        assert 'cost_estimate' in result
        
        # Verify decision and execution
        assert result['trading_decision']['action'] in ['execute', 'hold', 'reject']
        assert result['execution_plan']['order_id'] is not None
        assert result['cost_estimate']['total_cost'] >= 0
    
    @pytest.mark.asyncio
    async def test_coordinate_agent_interactions(self, orchestrator, mock_crew):
        """Test agent coordination and data sharing"""
        initial_context = {
            'symbol': 'GOOGL',
            'current_price': 125.0,
            'analysis_requirements': ['technical', 'fundamental', 'sentiment']
        }
        
        # Mock sequential agent responses with context propagation
        orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
            'research_data': {
                'company_overview': {'sector': 'Technology', 'industry': 'Internet'},
                'financial_metrics': {'pe_ratio': 25.0, 'revenue_growth': 0.15},
                'market_sentiment': {'overall': 0.65, 'news_volume': 'medium'}
            },
            'next_agent_context': {
                'focus_areas': ['valuation', 'growth_trends'],
                'key_metrics': ['pe_ratio', 'revenue_growth']
            }
        })
        
        orchestrator.agents['ml_prediction_engineer'].run = AsyncMock(return_value={
            'ml_analysis': {
                'price_target': 135.0,
                'probability_up': 0.72,
                'feature_importance': {'pe_ratio': 0.25, 'revenue_growth': 0.35}
            },
            'next_agent_context': {
                'risk_factors': ['volatility', 'market_conditions'],
                'confidence_level': 0.75
            }
        })
        
        orchestrator.agents['chief_risk_officer'].run = AsyncMock(return_value={
            'risk_analysis': {
                'risk_score': 0.35,
                'key_risks': ['market_volatility', 'sector_concentration'],
                'mitigation_strategies': ['position_sizing', 'stop_loss']
            },
            'next_agent_context': {
                'risk_approved': True,
                'position_limits': {'max_size': 800, 'max_risk': 0.03}
            }
        })
        
        orchestrator.agents['execution_trader'].run = AsyncMock(return_value={
            'execution_strategy': {
                'strategy': 'adaptive_twap',
                'venue_selection': ['NASDAQ', 'NYSE'],
                'timing': 'market_hours'
            },
            'final_recommendation': 'execute_with_caution'
        })
        
        result = await orchestrator.coordinate_agent_interactions(initial_context)
        
        # Verify coordination flow
        assert 'interaction_summary' in result
        assert 'data_flow' in result
        assert 'final_decision' in result
        
        # Verify context propagation
        data_flow = result['data_flow']
        assert len(data_flow) == 4  # 4 agents in sequence
        
        # Verify each step has proper context
        for i, step in enumerate(data_flow):
            assert 'agent' in step
            assert 'input_context' in step
            assert 'output_data' in step
            assert 'context_passed' in step
    
    @pytest.mark.asyncio
    async def test_handle_failure_and_recovery(self, orchestrator, mock_crew):
        """Test failure handling and recovery mechanisms"""
        failure_request = {
            'symbol': 'INVALID_SYMBOL',
            'tolerance_for_failures': 0.2,
            'recovery_strategy': 'retry_with_fallback'
        }
        
        # Configure some agents to fail
        orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
            'status': 'failed',
            'error': 'Symbol not found',
            'retry_count': 3
        })
        
        orchestrator.agents['ml_prediction_engineer'].run = AsyncMock(return_value={
            'status': 'partial_success',
            'predictions': [100.0],  # Fallback prediction
            'confidence': 0.50
        })
        
        orchestrator.agents['chief_risk_officer'].run = AsyncMock(return_value={
            'status': 'recovered',
            'risk_assessment': {'fallback_method': 'historical'},
            'risk_score': 0.40
        })
        
        orchestrator.agents['execution_trader'].run = AsyncMock(return_value={
            'status': 'skipped',
            'reason': 'Insufficient analysis data'
        })
        
        result = await orchestrator.handle_failure_and_recovery(failure_request)
        
        # Verify failure handling
        assert 'failure_analysis' in result
        assert 'recovery_actions' in result
        assert 'final_status' in result
        
        # Verify recovery summary
        recovery = result['recovery_actions']
        assert 'retry_attempts' in recovery
        assert 'fallback_strategies' in recovery
        assert 'affected_agents' in recovery
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, orchestrator, mock_crew):
        """Test performance monitoring and optimization"""
        # Run a workflow to generate performance data
        performance_request = {
            'symbol': 'TSLA',
            'monitoring': {
                'track_timing': True,
                'track_quality': True,
                'track_costs': True
            }
        }
        
        # Mock agent responses with timing information
        orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
            'processing_time': 2.5,
            'data_quality': 0.95,
            'cost': 0.05
        })
        
        orchestrator.agents['ml_prediction_engineer'].run = AsyncMock(return_value={
            'processing_time': 5.2,
            'model_accuracy': 0.87,
            'cost': 0.12
        })
        
        orchestrator.agents['chief_risk_officer'].run = AsyncMock(return_value={
            'processing_time': 1.8,
            'risk_assessment_quality': 0.92,
            'cost': 0.03
        })
        
        orchestrator.agents['execution_trader'].run = AsyncMock(return_value={
            'processing_time': 3.1,
            'execution_quality': 0.88,
            'cost': 0.08
        })
        
        result = await orchestrator.performance_monitoring(performance_request)
        
        # Verify performance metrics
        assert 'agent_performance' in result
        assert 'overall_metrics' in result
        assert 'optimization_recommendations' in result
        
        # Verify individual agent metrics
        agent_perf = result['agent_performance']
        for agent_name in orchestrator.agents:
            assert agent_name in agent_perf
            assert 'processing_time' in agent_perf[agent_name]
            assert 'quality_score' in agent_perf[agent_name]
            assert 'cost' in agent_perf[agent_name]
        
        # Verify overall metrics
        overall = result['overall_metrics']
        assert 'total_processing_time' in overall
        assert 'average_quality' in overall
        assert 'total_cost' in overall
    
    @pytest.mark.asyncio
    async def test_workflow_persistence(self, orchestrator, mock_crew):
        """Test workflow state persistence and resumption"""
        workflow_request = {
            'symbol': 'AMZN',
            'persistent': True,
            'resume_from_step': 'market_research'
        }
        
        # Mock saved workflow state
        saved_state = {
            'workflow_id': 'wf_12345',
            'current_step': 'market_research',
            'completed_steps': [],
            'agent_results': {},
            'context_data': {'symbol': 'AMZN'}
        }
        
        with patch.object(orchestrator.memory_manager, 'get_workflow_state') as mock_get_state:
            mock_get_state.return_value = saved_state
            
            # Mock market research agent to complete workflow
            orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
                'market_data': {'price': 120.0, 'trend': 'bullish'},
                'workflow_id': 'wf_12345'
            })
            
            # Continue with remaining agents
            for agent_name in ['ml_prediction_engineer', 'chief_risk_officer', 'execution_trader']:
                orchestrator.agents[agent_name].run = AsyncMock(return_value={
                    f'{agent_name}_result': 'completed',
                    'workflow_id': 'wf_12345'
                })
            
            result = await orchestrator.workflow_persistence(workflow_request)
            
            # Verify persistence
            assert 'workflow_resumption' in result
            assert 'state_saved' in result
            assert 'completion_status' in result
            
            # Verify workflow ID consistency
            assert result['workflow_id'] == saved_state['workflow_id']
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, orchestrator, mock_crew):
        """Test multiple concurrent workflows"""
        workflow_requests = [
            {'symbol': 'AAPL', 'priority': 'high', 'timeout': 30},
            {'symbol': 'MSFT', 'priority': 'medium', 'timeout': 45},
            {'symbol': 'GOOGL', 'priority': 'low', 'timeout': 60}
        ]
        
        # Mock agents to handle concurrent requests
        async def mock_agent_response(request):
            # Simulate processing time based on priority
            priority = request.get('priority', 'medium')
            processing_time = {'high': 1.0, 'medium': 1.5, 'low': 2.0}.get(priority, 1.5)
            await asyncio.sleep(processing_time / 10)  # Scale down for testing
            
            return {
                'symbol': request['symbol'],
                'priority': request['priority'],
                'status': 'completed',
                'processing_time': processing_time
            }
        
        for agent in orchestrator.agents.values():
            agent.run = mock_agent_response
        
        # Execute concurrent workflows
        results = await asyncio.gather(*[
            orchestrator.execute_market_analysis_workflow(req) for req in workflow_requests
        ])
        
        # Verify all workflows completed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result['symbol'] == workflow_requests[i]['symbol']
            assert result['status'] == 'completed'
            assert 'workflow_id' in result
    
    @pytest.mark.asyncio
    async def test_workflow_caching(self, orchestrator, mock_crew):
        """Test workflow result caching"""
        cache_request = {
            'symbol': 'NVDA',
            'use_cache': True,
            'cache_ttl': 300,  # 5 minutes
            'force_refresh': False
        }
        
        # First request should miss cache
        with patch.object(orchestrator.cache_manager, 'get') as mock_cache_get:
            mock_cache_get.return_value = None  # Cache miss
            
            orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
                'market_data': {'price': 200.0, 'cached': False}
            })
            
            # Mock cache set for first request
            with patch.object(orchestrator.cache_manager, 'set') as mock_cache_set:
                mock_cache_set.return_value = True
                
                result1 = await orchestrator.execute_market_analysis_workflow(cache_request)
                
                # Verify cache miss and data generation
                assert 'cache_status' in result1
                assert result1['cache_status'] == 'miss'
                
                # Second request should hit cache
                mock_cache_get.return_value = {
                    'symbol': 'NVDA',
                    'market_data': {'price': 200.0, 'cached': True},
                    'cached_at': datetime.now().isoformat()
                }
                
                result2 = await orchestrator.execute_market_analysis_workflow(cache_request)
                
                # Verify cache hit
                assert 'cache_status' in result2
                assert result2['cache_status'] == 'hit'
                assert result2['market_data']['cached'] is True
    
    @pytest.mark.asyncio
    async def test_error_handling_and_validation(self, orchestrator, mock_crew):
        """Test comprehensive error handling"""
        invalid_requests = [
            {'symbol': ''},  # Empty symbol
            {'symbol': None},  # None symbol
            {'symbol': 'INVALID'},  # Invalid symbol format
            {'analysis_requirements': []},  # Empty requirements
        ]
        
        for invalid_request in invalid_requests:
            with pytest.raises(Exception):
                await orchestrator.execute_market_analysis_workflow(invalid_request)
        
        # Test timeout handling
        timeout_request = {
            'symbol': 'SLOW_SYMBOL',
            'timeout': 1.0,  # Very short timeout
            'timeout_strategy': 'fail_fast'
        }
        
        # Mock slow agent response
        orchestrator.agents['market_research_analyst'].run = AsyncMock(side_effect=asyncio.TimeoutError())
        
        with pytest.raises(asyncio.TimeoutError):
            await orchestrator.execute_market_analysis_workflow(timeout_request)
    
    @pytest.mark.asyncio
    async def test_workflow_optimization(self, orchestrator, mock_crew):
        """Test workflow optimization and dynamic routing"""
        optimization_request = {
            'symbol': 'META',
            'optimization': {
                'enable_parallel': True,
                'skip_unnecessary_steps': True,
                'use_fast_models': True
            },
            'performance_targets': {
                'max_time': 5.0,
                'min_quality': 0.85,
                'max_cost': 0.10
            }
        }
        
        # Mock optimized agent responses
        orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
            'market_data': {'price': 250.0},
            'optimization_note': 'used_fast_api',
            'processing_time': 1.2
        })
        
        orchestrator.agents['ml_prediction_engineer'].run = AsyncMock(return_value={
            'predictions': [252.0, 254.0, 256.0],
            'optimization_note': 'used_lightweight_model',
            'processing_time': 0.8
        })
        
        # Skip risk officer for this optimized workflow
        orchestrator.agents['chief_risk_officer'].run = AsyncMock(return_value={
            'status': 'skipped',
            'reason': 'low_risk_symbol'
        })
        
        orchestrator.agents['execution_trader'].run = AsyncMock(return_value={
            'execution_plan': {'strategy': 'market_order'},
            'optimization_note': 'fast_execution',
            'processing_time': 0.5
        })
        
        result = await orchestrator.workflow_optimization(optimization_request)
        
        # Verify optimization results
        assert 'optimization_metrics' in result
        assert 'execution_plan' in result
        assert 'cost_breakdown' in result
        
        # Verify time savings
        metrics = result['optimization_metrics']
        assert 'total_time' in metrics
        assert 'time_savings' in metrics
        assert 'quality_retention' in metrics
        
        # Verify skip logic
        assert 'skipped_agents' in result
        assert 'chief_risk_officer' in result['skipped_agents']
    
    @pytest.mark.asyncio
    async def test_workflow_metrics_collection(self, orchestrator, mock_crew):
        """Test comprehensive metrics collection"""
        metrics_request = {
            'symbol': 'AMD',
            'collect_detailed_metrics': True,
            'metrics': [
                'timing', 'quality', 'cost', 'accuracy', 'user_satisfaction'
            ]
        }
        
        # Mock detailed agent metrics
        orchestrator.agents['market_research_analyst'].run = AsyncMock(return_value={
            'market_data': {'price': 75.0},
            'metrics': {
                'data_freshness': 0.95,
                'source_diversity': 8,
                'analysis_depth': 'comprehensive'
            }
        })
        
        orchestrator.agents['ml_prediction_engineer'].run = AsyncMock(return_value={
            'predictions': [76.0, 77.0],
            'metrics': {
                'model_accuracy': 0.89,
                'prediction_latency': 0.5,
                'feature_count': 45
            }
        })
        
        orchestrator.agents['chief_risk_officer'].run = AsyncMock(return_value={
            'risk_assessment': {'score': 0.3},
            'metrics': {
                'regulatory_compliance': 1.0,
                'risk_model_sophistication': 'advanced'
            }
        })
        
        orchestrator.agents['execution_trader'].run = AsyncMock(return_value={
            'execution_plan': {'strategy': 'twap'},
            'metrics': {
                'expected_slippage': 0.002,
                'venue_liquidity_score': 0.87,
                'cost_efficiency': 0.92
            }
        })
        
        result = await orchestrator.workflow_metrics_collection(metrics_request)
        
        # Verify detailed metrics
        assert 'agent_metrics' in result
        assert 'workflow_metrics' in result
        assert 'performance_score' in result
        assert 'improvement_suggestions' in result
        
        # Verify individual agent metrics
        agent_metrics = result['agent_metrics']
        for agent_name in orchestrator.agents:
            assert agent_name in agent_metrics
            assert isinstance(agent_metrics[agent_name], dict)
        
        # Verify workflow-level metrics
        workflow_metrics = result['workflow_metrics']
        assert 'end_to_end_time' in workflow_metrics
        assert 'overall_quality_score' in workflow_metrics
        assert 'cost_per_analysis' in workflow_metrics