"""
Unit tests for Chief Risk Officer Agent
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Import the agent
from agents.chief_risk_officer import ChiefRiskOfficer
from config.settings import TradingSettings


class TestChiefRiskOfficer:
    """Test cases for Chief Risk Officer"""
    
    @pytest.fixture
    def cro(self):
        """Create Chief Risk Officer instance"""
        return ChiefRiskOfficer()
    
    @pytest.fixture
    def mock_tools(self):
        """Mock tools for testing"""
        with patch('agents.chief_risk_officer.RiskCalculationTool') as mock_risk_tool, \
             patch('agents.chief_risk_officer.PositionSizingTool') as mock_position_tool, \
             patch('agents.chief_risk_officer.ComplianceTool') as mock_compliance_tool, \
             patch('agents.chief_risk_officer.StressTestingTool') as mock_stress_tool:
            
            # Configure mock risk tool
            mock_risk_tool.return_value.run = AsyncMock(return_value={
                'var_95': 0.05,
                'var_99': 0.08,
                'expected_shortfall': 0.07,
                'volatility': 0.25,
                'correlation': 0.6,
                'beta': 1.2
            })
            
            # Configure mock position sizing tool
            mock_position_tool.return_value.run = AsyncMock(return_value={
                'max_position_size': 1000,
                'position_weight': 0.10,
                'kelly_fraction': 0.25,
                'risk_budget': 0.02
            })
            
            # Configure mock compliance tool
            mock_compliance_tool.return_value.run = AsyncMock(return_value={
                'compliance_status': 'passed',
                'violations': [],
                'warnings': [],
                'risk_limits': {
                    'max_position_size': 0.10,
                    'max_sector_exposure': 0.25,
                    'max_single_stock': 0.05
                }
            })
            
            # Configure mock stress testing tool
            mock_stress_tool.return_value.run = AsyncMock(return_value={
                'stress_scenarios': {
                    'market_crash': {'loss_pct': -0.15, 'probability': 0.05},
                    'sector_rotation': {'loss_pct': -0.08, 'probability': 0.15},
                    'correlation_breakdown': {'loss_pct': -0.12, 'probability': 0.10}
                },
                'stress_var': 0.18,
                'stress_expected_shortfall': 0.22
            })
            
            yield {
                'risk': mock_risk_tool.return_value,
                'position': mock_position_tool.return_value,
                'compliance': mock_compliance_tool.return_value,
                'stress': mock_stress_tool.return_value
            }
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, cro):
        """Test agent initialization"""
        assert cro.name == "Chief Risk Officer"
        assert cro.role == "Risk Management & Compliance Specialist"
        assert len(cro.tools) > 0
        
        # Check that all expected tools are present
        tool_names = [tool.__class__.__name__ for tool in cro.tools]
        expected_tools = [
            'RiskCalculationTool', 
            'PositionSizingTool', 
            'ComplianceTool', 
            'StressTestingTool'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_assess_trade_risk(self, cro, mock_tools):
        """Test trade risk assessment functionality"""
        trade_request = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'price': 105.50,
            'order_type': 'limit'
        }
        
        result = await cro.assess_trade_risk(trade_request)
        
        # Verify structure
        assert 'trade_request' in result
        assert 'risk_metrics' in result
        assert 'risk_score' in result
        assert 'recommendation' in result
        assert 'risk_factors' in result
        
        # Verify values
        assert result['risk_metrics']['var_95'] == 0.05
        assert result['risk_metrics']['volatility'] == 0.25
        assert 0 <= result['risk_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_calculate_var(self, cro, mock_tools):
        """Test Value at Risk calculation"""
        portfolio_data = {
            'positions': {
                'AAPL': {'quantity': 100, 'price': 105.0},
                'MSFT': {'quantity': 50, 'price': 300.0}
            },
            'risk_free_rate': 0.02,
            'confidence_level': 0.95
        }
        
        result = await cro.calculate_var(portfolio_data)
        
        # Verify structure
        assert 'var_value' in result
        assert 'expected_shortfall' in result
        assert 'confidence_interval' in result
        assert 'historical_context' in result
        
        # Verify values
        assert isinstance(result['var_value'], (int, float))
        assert isinstance(result['expected_shortfall'], (int, float))
        assert result['var_value'] > 0
    
    @pytest.mark.asyncio
    async def test_check_compliance(self, cro, mock_tools):
        """Test compliance checking functionality"""
        compliance_request = {
            'action': 'execute_trade',
            'symbol': 'AAPL',
            'quantity': 100,
            'portfolio': {
                'total_value': 100000,
                'positions': {
                    'AAPL': {'quantity': 50, 'weight': 0.0525},
                    'MSFT': {'quantity': 25, 'weight': 0.075}
                }
            }
        }
        
        result = await cro.check_compliance(compliance_request)
        
        # Verify structure
        assert 'compliance_status' in result
        assert 'violations' in result
        assert 'warnings' in result
        assert 'remaining_capacity' in result
        
        # Verify compliance status
        assert result['compliance_status'] in ['passed', 'failed', 'warning']
        assert isinstance(result['violations'], list)
        assert isinstance(result['warnings'], list)
    
    @pytest.mark.asyncio
    async def test_calculate_position_size(self, cro, mock_tools):
        """Test position sizing calculation"""
        position_request = {
            'symbol': 'AAPL',
            'strategy_type': 'long_short',
            'risk_budget': 0.02,
            'confidence_level': 0.95,
            'stop_loss': 0.05,
            'take_profit': 0.15
        }
        
        result = await cro.calculate_position_size(position_request)
        
        # Verify structure
        assert 'recommended_size' in result
        assert 'position_weight' in result
        assert 'risk_metrics' in result
        assert 'kelly_fraction' in result
        
        # Verify values
        assert isinstance(result['recommended_size'], (int, float))
        assert isinstance(result['position_weight'], (int, float))
        assert 0 <= result['position_weight'] <= 1
        assert 0 <= result['kelly_fraction'] <= 1
    
    @pytest.mark.asyncio
    async def test_stress_test_portfolio(self, cro, mock_tools):
        """Test portfolio stress testing"""
        portfolio_data = {
            'positions': {
                'AAPL': {'quantity': 100, 'weight': 0.30},
                'MSFT': {'quantity': 50, 'weight': 0.25},
                'GOOGL': {'quantity': 30, 'weight': 0.25},
                'AMZN': {'quantity': 20, 'weight': 0.20}
            },
            'total_value': 100000,
            'sector_allocation': {
                'Technology': 1.0,
                'Consumer Discretionary': 0.0
            }
        }
        
        result = await cro.stress_test_portfolio(portfolio_data)
        
        # Verify structure
        assert 'stress_scenarios' in result
        assert 'portfolio_var' in result
        assert 'worst_case_loss' in result
        assert 'recovery_metrics' in result
        
        # Verify stress scenarios
        scenarios = result['stress_scenarios']
        assert 'market_crash' in scenarios
        assert 'sector_rotation' in scenarios
        assert 'correlation_breakdown' in scenarios
        
        for scenario in scenarios.values():
            assert 'loss_pct' in scenario
            assert 'probability' in scenario
            assert -1 <= scenario['loss_pct'] <= 0
            assert 0 <= scenario['probability'] <= 1
    
    @pytest.mark.asyncio
    async def test_monitoring_alerts(self, cro, mock_tools):
        """Test risk monitoring and alerting"""
        portfolio_data = {
            'current_positions': {
                'AAPL': {'quantity': 100, 'current_price': 105.0, 'avg_price': 100.0},
                'MSFT': {'quantity': 50, 'current_price': 300.0, 'avg_price': 295.0}
            },
            'risk_limits': {
                'max_drawdown': 0.15,
                'max_var': 0.08,
                'max_sector_exposure': 0.30
            }
        }
        
        result = await cro.monitoring_alerts(portfolio_data)
        
        # Verify structure
        assert 'risk_status' in result
        assert 'active_alerts' in result
        assert 'risk_metrics' in result
        assert 'recommendations' in result
        
        # Verify risk status
        assert result['risk_status'] in ['normal', 'warning', 'critical']
        assert isinstance(result['active_alerts'], list)
        assert isinstance(result['recommendations'], list)
    
    @pytest.mark.asyncio
    async def test_calculate_correlation_matrix(self, cro):
        """Test correlation matrix calculation"""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        # Mock price data
        price_data = pd.DataFrame({
            symbol: np.random.uniform(100, 200, 100) for symbol in symbols
        })
        
        with patch.object(cro, 'get_historical_data') as mock_get_data:
            mock_get_data.return_value = price_data
            
            result = await cro.calculate_correlation_matrix(symbols)
            
            # Verify structure
            assert 'correlation_matrix' in result
            assert 'eigenvalues' in result
            assert 'diversification_ratio' in result
            
            # Verify matrix properties
            matrix = result['correlation_matrix']
            assert isinstance(matrix, pd.DataFrame)
            assert matrix.shape == (len(symbols), len(symbols))
            assert all(abs(matrix.iloc[i, i]) == 1.0 for i in range(len(symbols)))  # Diagonal = 1
    
    @pytest.mark.asyncio
    async def test_risk_parity_allocation(self, cro, mock_tools):
        """Test risk parity allocation"""
        allocation_request = {
            'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN'],
            'target_volatility': 0.15,
            'risk_free_rate': 0.02,
            'lookback_period': 252
        }
        
        result = await cro.risk_parity_allocation(allocation_request)
        
        # Verify structure
        assert 'target_weights' in result
        assert 'expected_volatility' in result
        assert 'risk_contributions' in result
        assert 'optimization_metrics' in result
        
        # Verify weights
        weights = result['target_weights']
        assert isinstance(weights, dict)
        assert abs(sum(weights.values()) - 1.0) < 0.01  # Weights sum to 1
        assert all(weight >= 0 for weight in weights.values())  # No short positions
    
    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio(self, cro, mock_tools):
        """Test Sharpe ratio calculation"""
        portfolio_data = {
            'returns': np.random.normal(0.01, 0.02, 252),
            'benchmark_returns': np.random.normal(0.008, 0.015, 252),
            'risk_free_rate': 0.02,
            'annualized': True
        }
        
        result = await cro.calculate_sharpe_ratio(portfolio_data)
        
        # Verify structure
        assert 'sharpe_ratio' in result
        assert 'information_ratio' in result
        assert 'sortino_ratio' in result
        assert 'calmar_ratio' in result
        
        # Verify values
        assert isinstance(result['sharpe_ratio'], (int, float))
        assert isinstance(result['information_ratio'], (int, float))
        assert isinstance(result['sortino_ratio'], (int, float))
    
    @pytest.mark.asyncio
    async def test_monte_carlo_simulation(self, cro):
        """Test Monte Carlo risk simulation"""
        simulation_config = {
            'initial_capital': 100000,
            'num_simulations': 1000,
            'time_horizon': 252,  # 1 year
            'return_distribution': 'normal',
            'mean_return': 0.10,
            'volatility': 0.20
        }
        
        with patch('numpy.random.normal') as mock_normal:
            mock_normal.return_value = np.random.normal(0, 1, 1000)
            
            result = await cro.monte_carlo_simulation(simulation_config)
            
            # Verify structure
            assert 'final_portfolio_values' in result
            assert 'percentiles' in result
            assert 'probability_of_loss' in result
            assert 'expected_value' in result
            
            # Verify percentiles
            percentiles = result['percentiles']
            assert 'p5' in percentiles
            assert 'p25' in percentiles
            assert 'p50' in percentiles
            assert 'p75' in percentiles
            assert 'p95' in percentiles
    
    @pytest.mark.asyncio
    async def test_risk_attribution(self, cro, mock_tools):
        """Test risk attribution analysis"""
        attribution_request = {
            'portfolio': {
                'total_value': 100000,
                'positions': {
                    'AAPL': {'weight': 0.25, 'volatility': 0.30},
                    'MSFT': {'weight': 0.20, 'volatility': 0.25},
                    'GOOGL': {'weight': 0.30, 'volatility': 0.35},
                    'AMZN': {'weight': 0.25, 'volatility': 0.40}
                }
            },
            'attribution_type': 'marginal'
        }
        
        result = await cro.risk_attribution(attribution_request)
        
        # Verify structure
        assert 'risk_contributions' in result
        assert 'total_portfolio_risk' in result
        assert 'diversification_benefit' in result
        assert 'risk_concentration' in result
        
        # Verify contributions
        contributions = result['risk_contributions']
        assert len(contributions) == 4  # 4 positions
        assert abs(sum(contributions.values()) - result['total_portfolio_risk']) < 0.01
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self, cro):
        """Test error handling for invalid data"""
        # Test with empty portfolio
        with pytest.raises(ValueError):
            await cro.calculate_var({})
        
        # Test with invalid trade request
        with pytest.raises(ValueError):
            await cro.assess_trade_risk({})
    
    @pytest.mark.asyncio
    async def test_error_handling_api_failure(self, cro, mock_tools):
        """Test error handling for API failures"""
        # Configure mock to raise exception
        mock_tools['risk'].run.side_effect = Exception("Risk calculation failed")
        
        trade_request = {
            'symbol': 'INVALID',
            'side': 'buy',
            'quantity': 100
        }
        
        with pytest.raises(Exception, match="Risk calculation failed"):
            await cro.assess_trade_risk(trade_request)
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, cro, performance_monitor):
        """Test performance metrics"""
        performance_monitor.start()
        
        # Simulate risk calculation
        await asyncio.sleep(0.01)
        
        execution_time = performance_monitor.stop()
        
        # Should complete within reasonable time
        assert execution_time < 1.0
    
    @pytest.mark.asyncio
    async def test_concurrent_risk_assessments(self, cro):
        """Test concurrent risk assessments"""
        trade_requests = [
            {'symbol': 'AAPL', 'side': 'buy', 'quantity': 100},
            {'symbol': 'MSFT', 'side': 'sell', 'quantity': 50},
            {'symbol': 'GOOGL', 'side': 'buy', 'quantity': 75},
            {'symbol': 'AMZN', 'side': 'buy', 'quantity': 25}
        ]
        
        with patch.object(cro, 'assess_trade_risk') as mock_assess:
            mock_assess.side_effect = lambda req: {'risk_score': 0.5, 'symbol': req['symbol']}
            
            results = await asyncio.gather(*[
                cro.assess_trade_risk(req) for req in trade_requests
            ])
            
            # Verify all assessments completed
            assert len(results) == 4
            for i, result in enumerate(results):
                assert result['symbol'] == trade_requests[i]['symbol']
                assert 'risk_score' in result
    
    @pytest.mark.asyncio
    async def test_risk_limit_validation(self, cro, mock_tools):
        """Test risk limit validation"""
        portfolio_data = {
            'current_exposure': {
                'sector_tech': 0.85,  # Above 25% limit
                'single_stock': 0.15,  # Above 5% limit
                'total_exposure': 1.5  # High leverage
            },
            'risk_limits': {
                'max_sector_exposure': 0.25,
                'max_single_stock': 0.05,
                'max_leverage': 2.0
            }
        }
        
        result = await cro.risk_limit_validation(portfolio_data)
        
        # Verify violations detected
        assert 'violations' in result
        assert len(result['violations']) > 0
        
        # Check specific violations
        violations = [v['type'] for v in result['violations']]
        assert 'sector_exposure' in violations
        assert 'single_stock' in violations
    
    @pytest.mark.asyncio
    async def test_scenario_analysis(self, cro, mock_tools):
        """Test scenario analysis"""
        scenario_request = {
            'base_portfolio': {
                'total_value': 100000,
                'positions': {'AAPL': 50000, 'MSFT': 50000}
            },
            'scenarios': [
                {
                    'name': 'tech_crash',
                    'description': 'Tech sector decline',
                    'market_shocks': {
                        'tech_sector': -0.30,
                        'market': -0.15
                    }
                },
                {
                    'name': 'fed_hike',
                    'description': 'Federal Reserve rate hike',
                    'market_shocks': {
                        'rates': 0.75,
                        'market': -0.10,
                        'tech_sector': -0.20
                    }
                }
            ]
        }
        
        result = await cro.scenario_analysis(scenario_request)
        
        # Verify structure
        assert 'scenario_results' in result
        assert 'base_case' in result
        assert 'risk_adjusted_returns' in result
        
        # Verify scenario results
        scenario_results = result['scenario_results']
        assert len(scenario_results) == 2
        assert 'tech_crash' in scenario_results
        assert 'fed_hike' in scenario_results
        
        for scenario_result in scenario_results.values():
            assert 'portfolio_value' in scenario_result
            assert 'loss_pct' in scenario_result
            assert 'probable_impact' in scenario_result


class TestRiskCalculationTool:
    """Test cases for RiskCalculationTool"""
    
    @pytest.fixture
    def risk_tool(self):
        """Create RiskCalculationTool instance"""
        from agents.tools.risk_calculation_tool import RiskCalculationTool
        return RiskCalculationTool()
    
    @pytest.mark.asyncio
    async def test_var_calculation(self, risk_tool, sample_market_data):
        """Test Value at Risk calculation"""
        portfolio_data = {
            'positions': [
                {'symbol': 'AAPL', 'weight': 0.5, 'price': 105.0},
                {'symbol': 'MSFT', 'weight': 0.5, 'price': 300.0}
            ],
            'confidence_level': 0.95,
            'time_horizon': 1
        }
        
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = sample_market_data
            
            result = await risk_tool.run(portfolio_data)
            
            assert 'var_95' in result
            assert 'var_99' in result
            assert 'expected_shortfall' in result
            assert result['var_95'] > 0
    
    @pytest.mark.asyncio
    async def test_volatility_calculation(self, risk_tool):
        """Test volatility calculation"""
        symbol = "AAPL"
        
        # Mock return series
        returns = np.random.normal(0.001, 0.02, 252)
        
        with patch('numpy.std') as mock_std:
            mock_std.return_value = 0.02
            
            result = await risk_tool.run({'symbol': symbol, 'calculate': 'volatility'})
            
            assert 'annualized_volatility' in result
            assert 'daily_volatility' in result
            assert result['annualized_volatility'] > 0
    
    @pytest.mark.asyncio
    async def test_correlation_calculation(self, risk_tool):
        """Test correlation calculation"""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        # Mock price data
        price_data = pd.DataFrame({
            symbol: np.random.uniform(100, 200, 100) for symbol in symbols
        })
        
        with patch.object(risk_tool, 'get_price_data') as mock_get_data:
            mock_get_data.return_value = price_data
            
            result = await risk_tool.run({'symbols': symbols, 'calculate': 'correlation'})
            
            assert 'correlation_matrix' in result
            assert 'average_correlation' in result
            assert result['correlation_matrix'].shape == (3, 3)


class TestPositionSizingTool:
    """Test cases for PositionSizingTool"""
    
    @pytest.fixture
    def position_tool(self):
        """Create PositionSizingTool instance"""
        from agents.tools.position_sizing_tool import PositionSizingTool
        return PositionSizingTool()
    
    @pytest.mark.asyncio
    async def test_kelly_criterion(self, position_tool):
        """Test Kelly Criterion position sizing"""
        strategy_data = {
            'win_rate': 0.55,
            'avg_win': 0.02,
            'avg_loss': 0.01,
            'total_capital': 100000
        }
        
        result = await position_tool.run(strategy_data, method='kelly')
        
        assert 'kelly_fraction' in result
        assert 'position_size' in result
        assert 'max_risk' in result
        assert 0 <= result['kelly_fraction'] <= 1
    
    @pytest.mark.asyncio
    async def test_fixed_risk_sizing(self, position_tool):
        """Test fixed risk position sizing"""
        trade_data = {
            'entry_price': 105.0,
            'stop_loss': 100.0,
            'risk_per_trade': 0.02,
            'account_size': 100000
        }
        
        result = await position_tool.run(trade_data, method='fixed_risk')
        
        assert 'position_size' in result
        assert 'position_value' in result
        assert 'risk_amount' in result
        assert result['position_size'] > 0
    
    @pytest.mark.asyncio
    async def test_volatility_adjusted_sizing(self, position_tool):
        """Test volatility-adjusted position sizing"""
        trade_data = {
            'symbol': 'AAPL',
            'volatility': 0.25,
            'target_volatility': 0.15,
            'account_size': 100000
        }
        
        with patch('numpy.sqrt') as mock_sqrt:
            mock_sqrt.return_value = 1.0
            
            result = await position_tool.run(trade_data, method='volatility_adj')
            
            assert 'position_size' in result
            assert 'volatility_adjustment' in result
            assert result['volatility_adjustment'] > 0


class TestComplianceTool:
    """Test cases for ComplianceTool"""
    
    @pytest.fixture
    def compliance_tool(self):
        """Create ComplianceTool instance"""
        from agents.tools.compliance_tool import ComplianceTool
        return ComplianceTool()
    
    @pytest.mark.asyncio
    async def test_position_limits(self, compliance_tool):
        """Test position limit compliance"""
        portfolio_data = {
            'positions': {
                'AAPL': {'value': 15000, 'weight': 0.15},  # Above 10% limit
                'MSFT': {'value': 5000, 'weight': 0.05}
            },
            'limits': {
                'max_single_position': 0.10,
                'max_portfolio_value': 100000
            }
        }
        
        result = await compliance_tool.run(portfolio_data, check_type='position_limits')
        
        assert 'violations' in result
        assert len(result['violations']) > 0
        assert any('AAPL' in v['description'] for v in result['violations'])
    
    @pytest.mark.asyncio
    async def test_sector_limits(self, compliance_tool):
        """Test sector exposure limits"""
        portfolio_data = {
            'sector_allocation': {
                'Technology': 0.85,  # Above 75% limit
                'Consumer Discretionary': 0.15
            },
            'limits': {
                'max_sector_exposure': 0.75
            }
        }
        
        result = await compliance_tool.run(portfolio_data, check_type='sector_limits')
        
        assert 'violations' in result
        assert len(result['violations']) > 0
        assert any('Technology' in v['description'] for v in result['violations'])
    
    @pytest.mark.asyncio
    async def test_concentration_risk(self, compliance_tool):
        """Test concentration risk assessment"""
        portfolio_data = {
            'positions': {
                f'STOCK_{i:03d}': {'weight': 0.001} for i in range(1, 51)
            },
            'limits': {
                'min_diversification': 20,
                'max_single_weight': 0.05
            }
        }
        
        result = await compliance_tool.run(portfolio_data, check_type='concentration')
        
        assert 'diversification_score' in result
        assert 'concentration_risk' in result
        assert 0 <= result['diversification_score'] <= 1


class TestStressTestingTool:
    """Test cases for StressTestingTool"""
    
    @pytest.fixture
    def stress_tool(self):
        """Create StressTestingTool instance"""
        from agents.tools.stress_testing_tool import StressTestingTool
        return StressTestingTool()
    
    @pytest.mark.asyncio
    async def test_historical_scenarios(self, stress_tool):
        """Test historical scenario stress testing"""
        portfolio_data = {
            'positions': {
                'AAPL': {'weight': 0.4},
                'MSFT': {'weight': 0.3},
                'GOOGL': {'weight': 0.3}
            }
        }
        
        # Mock historical data
        historical_scenarios = {
            '2008_crisis': {'market_return': -0.37, 'tech_return': -0.45},
            '2020_covid': {'market_return': -0.34, 'tech_return': -0.25},
            '2022_bear': {'market_return': -0.18, 'tech_return': -0.35}
        }
        
        with patch.object(stress_tool, 'get_historical_scenarios') as mock_scenarios:
            mock_scenarios.return_value = historical_scenarios
            
            result = await stress_tool.run(portfolio_data, scenario_type='historical')
            
            assert 'scenario_results' in result
            assert len(result['scenario_results']) == 3
            for scenario_name in ['2008_crisis', '2020_covid', '2022_bear']:
                assert scenario_name in result['scenario_results']
                assert 'portfolio_loss' in result['scenario_results'][scenario_name]
    
    @pytest.mark.asyncio
    async def test_custom_scenarios(self, stress_tool):
        """Test custom scenario stress testing"""
        portfolio_data = {
            'positions': {'AAPL': {'weight': 1.0}}
        }
        
        custom_scenarios = [
            {
                'name': 'tech_crash',
                'description': 'Tech sector crash',
                'shock_vector': {'tech_sector': -0.30},
                'probability': 0.10
            }
        ]
        
        result = await stress_tool.run(portfolio_data, 
                                     scenario_type='custom',
                                     scenarios=custom_scenarios)
        
        assert 'scenario_results' in result
        assert 'tech_crash' in result['scenario_results']
        assert result['scenario_results']['tech_crash']['probability'] == 0.10
    
    @pytest.mark.asyncio
    async def test_monte_carlo_stress(self, stress_tool):
        """Test Monte Carlo stress testing"""
        portfolio_data = {
            'positions': {'AAPL': {'weight': 0.5}, 'MSFT': {'weight': 0.5}},
            'simulation_params': {
                'num_simulations': 1000,
                'time_horizon': 21,  # 1 month
                'confidence_level': 0.95
            }
        }
        
        with patch('numpy.random.normal') as mock_normal:
            mock_normal.return_value = np.random.normal(0, 1, 1000)
            
            result = await stress_tool.run(portfolio_data, 
                                         scenario_type='monte_carlo')
            
            assert 'simulation_results' in result
            assert 'percentiles' in result
            assert 'stress_var' in result
            assert 'extreme_loss_probability' in result


class TestIntegration:
    """Integration tests for Chief Risk Officer"""
    
    @pytest.mark.asyncio
    async def test_risk_management_workflow(self):
        """Test complete risk management workflow"""
        from agents.chief_risk_officer import ChiefRiskOfficer
        
        cro = ChiefRiskOfficer()
        
        # Mock all tools
        with patch.multiple(
            'agents.chief_risk_officer.RiskCalculationTool',
            run=AsyncMock(return_value={'var_95': 0.05, 'volatility': 0.25})
        ), patch.multiple(
            'agents.chief_risk_officer.PositionSizingTool',
            run=AsyncMock(return_value={'position_size': 1000, 'risk_budget': 0.02})
        ), patch.multiple(
            'agents.chief_risk_officer.ComplianceTool',
            run=AsyncMock(return_value={'compliance_status': 'passed', 'violations': []})
        ), patch.multiple(
            'agents.chief_risk_officer.StressTestingTool',
            run=AsyncMock(return_value={'stress_var': 0.18, 'scenario_results': {}})
        ):
            
            # Simulate trade request
            trade_request = {
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 100,
                'price': 105.0
            }
            
            # Step 1: Assess risk
            risk_assessment = await cro.assess_trade_risk(trade_request)
            assert risk_assessment['risk_score'] >= 0
            
            # Step 2: Calculate position size
            position_request = {
                'symbol': 'AAPL',
                'risk_budget': 0.02,
                'confidence_level': 0.95
            }
            position_size = await cro.calculate_position_size(position_request)
            assert position_size['recommended_size'] > 0
            
            # Step 3: Check compliance
            compliance_request = {
                'action': 'execute_trade',
                'symbol': 'AAPL',
                'quantity': position_size['recommended_size']
            }
            compliance_result = await cro.check_compliance(compliance_request)
            assert compliance_result['compliance_status'] in ['passed', 'failed']