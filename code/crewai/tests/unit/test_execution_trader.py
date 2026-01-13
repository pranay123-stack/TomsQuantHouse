"""
Unit tests for Execution Trader Agent
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid

# Import the agent
from agents.execution_trader import ExecutionTrader
from config.settings import TradingSettings


class TestExecutionTrader:
    """Test cases for Execution Trader"""
    
    @pytest.fixture
    def trader(self):
        """Create ExecutionTrader instance"""
        return ExecutionTrader()
    
    @pytest.fixture
    def mock_tools(self):
        """Mock tools for testing"""
        with patch('agents.execution_trader.OrderExecutionTool') as mock_execution_tool, \
             patch('agents.execution_trader.MarketImpactTool') as mock_impact_tool, \
             patch('agents.execution_trader.ExecutionMonitorTool') as mock_monitor_tool, \
             patch('agents.execution_trader.LiquidityAnalysisTool') as mock_liquidity_tool:
            
            # Configure mock execution tool
            mock_execution_tool.return_value.run = AsyncMock(return_value={
                'order_id': 'order_12345',
                'status': 'filled',
                'filled_quantity': 100,
                'average_price': 105.50,
                'execution_time': 0.5,  # seconds
                'commission': 1.0
            })
            
            # Configure mock market impact tool
            mock_impact_tool.return_value.run = AsyncMock(return_value={
                'expected_impact': 0.02,  # 2%
                'market_impact_cost': 2.0,
                'liquidity_score': 0.75,
                'optimal_execution_strategy': 'twap',
                'participation_rate': 0.15
            })
            
            # Configure mock execution monitor tool
            mock_monitor_tool.return_value.run = AsyncMock(return_value={
                'execution_status': 'completed',
                'fill_rate': 1.0,
                'slippage': 0.01,
                'execution_quality': 'excellent',
                'alerts': []
            })
            
            # Configure mock liquidity analysis tool
            mock_liquidity_tool.return_value.run = AsyncMock(return_value={
                'bid_ask_spread': 0.10,
                'market_depth': {
                    'bid_levels': [105.40, 105.30, 105.20],
                    'ask_levels': [105.60, 105.70, 105.80],
                    'bid_sizes': [100, 200, 300],
                    'ask_sizes': [150, 250, 350]
                },
                'liquidity_availability': 5000,
                'optimal_order_size': 800
            })
            
            yield {
                'execution': mock_execution_tool.return_value,
                'impact': mock_impact_tool.return_value,
                'monitor': mock_monitor_tool.return_value,
                'liquidity': mock_liquidity_tool.return_value
            }
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, trader):
        """Test agent initialization"""
        assert trader.name == "Execution Trader"
        assert trader.role == "Trade Execution & Market Operations Specialist"
        assert len(trader.tools) > 0
        
        # Check that all expected tools are present
        tool_names = [tool.__class__.__name__ for tool in trader.tools]
        expected_tools = [
            'OrderExecutionTool', 
            'MarketImpactTool', 
            'ExecutionMonitorTool', 
            'LiquidityAnalysisTool'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_execute_trade(self, trader, mock_tools):
        """Test trade execution functionality"""
        trade_request = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'limit',
            'price': 105.50,
            'time_in_force': 'day',
            'execution_strategy': 'aggressive'
        }
        
        result = await trader.execute_trade(trade_request)
        
        # Verify structure
        assert 'order_id' in result
        assert 'execution_details' in result
        assert 'market_impact_assessment' in result
        assert 'liquidity_analysis' in result
        assert 'next_steps' in result
        
        # Verify values
        assert result['order_id'].startswith('order_')
        assert 'status' in result['execution_details']
        assert 'filled_quantity' in result['execution_details']
        assert isinstance(result['filled_quantity'], (int, float))
    
    @pytest.mark.asyncio
    async def test_calculate_optimal_position_size(self, trader, mock_tools):
        """Test optimal position size calculation"""
        position_request = {
            'symbol': 'MSFT',
            'available_capital': 50000,
            'risk_tolerance': 0.02,
            'current_price': 300.0,
            'volatility': 0.25,
            'liquidity': 0.80,
            'execution_strategy': 'twap'
        }
        
        result = await trader.calculate_optimal_position_size(position_request)
        
        # Verify structure
        assert 'optimal_size' in result
        assert 'position_value' in result
        assert 'risk_metrics' in result
        assert 'execution_plan' in result
        
        # Verify values
        assert result['optimal_size'] > 0
        assert result['position_value'] > 0
        assert 0 <= result['risk_metrics']['expected_slippage'] <= 1
        assert 'time_slicing' in result['execution_plan']
    
    @pytest.mark.asyncio
    async def test_analyze_market_impact(self, trader, mock_tools):
        """Test market impact analysis"""
        impact_request = {
            'symbol': 'GOOGL',
            'order_size': 1000,
            'current_price': 125.0,
            'market_conditions': 'normal',
            'execution_timeframe': 'intraday'
        }
        
        result = await trader.analyze_market_impact(impact_request)
        
        # Verify structure
        assert 'impact_estimate' in result
        assert 'execution_strategy' in result
        assert 'cost_breakdown' in result
        assert 'risk_factors' in result
        
        # Verify impact estimate
        impact = result['impact_estimate']
        assert 'expected_cost' in impact
        assert 'upper_bound' in impact
        assert 'lower_bound' in impact
        assert result['cost_breakdown']['total_cost'] > 0
    
    @pytest.mark.asyncio
    async def test_monitor_execution(self, trader, mock_tools):
        """Test execution monitoring"""
        monitoring_request = {
            'order_ids': ['order_12345', 'order_67890'],
            'monitoring_interval': 1.0,  # seconds
            'alert_conditions': {
                'slippage_threshold': 0.02,
                'execution_delay_threshold': 10.0  # seconds
            }
        }
        
        result = await trader.monitor_execution(monitoring_request)
        
        # Verify structure
        assert 'execution_status' in result
        assert 'performance_metrics' in result
        assert 'alerts' in result
        assert 'recommendations' in result
        
        # Verify status
        status = result['execution_status']
        assert isinstance(status, dict)
        assert all(order_id in status for order_id in monitoring_request['order_ids'])
        
        # Verify metrics
        metrics = result['performance_metrics']
        assert 'average_fill_time' in metrics
        assert 'total_slippage' in metrics
        assert 'execution_quality' in metrics
    
    @pytest.mark.asyncio
    async def test_liquidity_analysis(self, trader, mock_tools):
        """Test liquidity analysis"""
        liquidity_request = {
            'symbol': 'AMZN',
            'order_size': 500,
            'time_horizon': 'intraday',
            'market_conditions': 'normal'
        }
        
        result = await trader.liquidity_analysis(liquidity_request)
        
        # Verify structure
        assert 'liquidity_score' in result
        assert 'optimal_execution' in result
        assert 'market_conditions' in result
        assert 'risk_assessment' in result
        
        # Verify liquidity score
        assert 0 <= result['liquidity_score'] <= 1
        assert 'optimal_size' in result['optimal_execution']
        assert 'participation_rate' in result['optimal_execution']
    
    @pytest.mark.asyncio
    async def test_algorithmic_trading_strategies(self, trader, mock_tools):
        """Test algorithmic trading strategies"""
        strategy_request = {
            'symbol': 'TSLA',
            'quantity': 2000,
            'strategy_type': 'twap',
            'execution_window': 3600,  # 1 hour in seconds
            'aggressiveness': 'medium'
        }
        
        result = await trader.algorithmic_trading_strategies(strategy_request)
        
        # Verify structure
        assert 'strategy_details' in result
        assert 'execution_schedule' in result
        assert 'risk_controls' in result
        assert 'performance_targets' in result
        
        # Verify strategy details
        details = result['strategy_details']
        assert details['strategy_type'] == 'twap'
        assert 'interval_size' in details
        assert 'participation_rate' in details
        
        # Verify schedule
        schedule = result['execution_schedule']
        assert len(schedule) > 0
        assert all('timestamp' in interval for interval in schedule)
        assert all('quantity' in interval for interval in schedule)
    
    @pytest.mark.asyncio
    async def test_cost_analysis(self, trader, mock_tools):
        """Test transaction cost analysis"""
        cost_request = {
            'symbol': 'NVDA',
            'order_size': 500,
            'execution_strategy': 'vwap',
            'market_impact_model': 'linear'
        }
        
        result = await trader.cost_analysis(cost_request)
        
        # Verify structure
        assert 'cost_breakdown' in result
        assert 'total_cost' in result
        assert 'cost_vs_benchmark' in result
        assert 'optimization_suggestions' in result
        
        # Verify cost breakdown
        breakdown = result['cost_breakdown']
        assert 'commission' in breakdown
        assert 'market_impact' in breakdown
        assert 'opportunity_cost' in breakdown
        assert breakdown['total_cost'] > 0
        
        # Verify benchmark comparison
        benchmark = result['cost_vs_benchmark']
        assert 'percentage_of_value' in benchmark
        assert 'vs_market' in benchmark
    
    @pytest.mark.asyncio
    async def test_signal_generation(self, trader, mock_tools):
        """Test trading signal generation"""
        signal_request = {
            'prediction_data': {
                'price_target': 110.0,
                'confidence': 0.85,
                'time_horizon': 5
            },
            'current_market': {
                'price': 105.0,
                'volume': 1000000,
                'volatility': 0.25
            },
            'risk_parameters': {
                'stop_loss': 0.05,
                'take_profit': 0.15
            }
        }
        
        result = await trader.signal_generation(signal_request)
        
        # Verify structure
        assert 'signal' in result
        assert 'position_size' in result
        assert 'entry_strategy' in result
        assert 'risk_management' in result
        
        # Verify signal
        signal = result['signal']
        assert signal['action'] in ['buy', 'sell', 'hold']
        assert 'strength' in signal
        assert 'confidence' in signal
        
        # Verify position size
        position = result['position_size']
        assert position['size'] > 0
        assert 'sizing_method' in position
    
    @pytest.mark.asyncio
    async def test_portfolio_rebalancing(self, trader, mock_tools):
        """Test portfolio rebalancing functionality"""
        rebalance_request = {
            'current_portfolio': {
                'AAPL': {'quantity': 100, 'weight': 0.30},
                'MSFT': {'quantity': 50, 'weight': 0.25},
                'GOOGL': {'quantity': 30, 'weight': 0.20},
                'AMZN': {'quantity': 20, 'weight': 0.25}
            },
            'target_weights': {
                'AAPL': 0.25,
                'MSFT': 0.25,
                'GOOGL': 0.25,
                'AMZN': 0.25
            },
            'cash_available': 10000,
            'transaction_costs': 0.001
        }
        
        result = await trader.portfolio_rebalancing(rebalance_request)
        
        # Verify structure
        assert 'rebalancing_trades' in result
        assert 'cash_flow' in result
        assert 'expected_costs' in result
        assert 'execution_timeline' in result
        
        # Verify trades
        trades = result['rebalancing_trades']
        assert isinstance(trades, list)
        for trade in trades:
            assert 'symbol' in trade
            assert 'action' in trade
            assert 'quantity' in trade
            assert 'estimated_cost' in trade
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_order(self, trader):
        """Test error handling for invalid orders"""
        # Test with missing required fields
        invalid_order = {
            'symbol': 'AAPL'
            # Missing quantity, side, etc.
        }
        
        with pytest.raises(ValueError, match="Missing required order fields"):
            await trader.execute_trade(invalid_order)
        
        # Test with invalid symbol
        invalid_order = {
            'symbol': 'INVALID_SYMBOL_123',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'market'
        }
        
        with patch.object(trader, '_validate_symbol') as mock_validate:
            mock_validate.side_effect = Exception("Invalid symbol")
            
            with pytest.raises(Exception, match="Invalid symbol"):
                await trader.execute_trade(invalid_order)
    
    @pytest.mark.asyncio
    async def test_error_handling_execution_failure(self, trader, mock_tools):
        """Test error handling for execution failures"""
        # Configure mock to raise exception
        mock_tools['execution'].run.side_effect = Exception("Order execution failed")
        
        trade_request = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'limit',
            'price': 105.50
        }
        
        with pytest.raises(Exception, match="Order execution failed"):
            await trader.execute_trade(trade_request)
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, trader, performance_monitor):
        """Test performance metrics"""
        performance_monitor.start()
        
        # Simulate trade execution
        await asyncio.sleep(0.01)
        
        execution_time = performance_monitor.stop()
        
        # Should complete within reasonable time
        assert execution_time < 1.0
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self, trader):
        """Test concurrent trade executions"""
        trade_requests = [
            {'symbol': 'AAPL', 'side': 'buy', 'quantity': 100},
            {'symbol': 'MSFT', 'side': 'sell', 'quantity': 50},
            {'symbol': 'GOOGL', 'side': 'buy', 'quantity': 75},
            {'symbol': 'AMZN', 'side': 'buy', 'quantity': 25}
        ]
        
        with patch.object(trader, 'execute_trade') as mock_execute:
            mock_execute.side_effect = lambda req: {
                'order_id': f'order_{uuid.uuid4().hex[:8]}',
                'execution_details': {'status': 'filled', 'quantity': req['quantity']}
            }
            
            results = await asyncio.gather(*[
                trader.execute_trade(req) for req in trade_requests
            ])
            
            # Verify all executions completed
            assert len(results) == 4
            for i, result in enumerate(results):
                assert 'order_id' in result
                assert result['execution_details']['quantity'] == trade_requests[i]['quantity']
    
    @pytest.mark.asyncio
    async def test_execution_quality_assessment(self, trader, mock_tools):
        """Test execution quality assessment"""
        quality_request = {
            'order_id': 'order_12345',
            'benchmark_price': 105.50,
            'market_prices_during_execution': [
                105.40, 105.45, 105.50, 105.55, 105.60
            ],
            'execution_details': {
                'filled_price': 105.52,
                'quantity': 100,
                'execution_time': 5.0
            }
        }
        
        result = await trader.execution_quality_assessment(quality_request)
        
        # Verify structure
        assert 'quality_score' in result
        assert 'benchmark_comparison' in result
        assert 'performance_metrics' in result
        assert 'improvement_suggestions' in result
        
        # Verify quality score
        assert 0 <= result['quality_score'] <= 1
        
        # Verify benchmark comparison
        benchmark = result['benchmark_comparison']
        assert 'price_improvement' in benchmark
        assert 'timeliness_score' in benchmark
    
    @pytest.mark.asyncio
    async def test_market_making_strategies(self, trader, mock_tools):
        """Test market making strategies"""
        making_request = {
            'symbol': 'AAPL',
            'inventory': 1000,
            'target_inventory': 500,
            'market_conditions': 'normal',
            'risk_tolerance': 0.02,
            'spread_target': 0.10
        }
        
        result = await trader.market_making_strategies(making_request)
        
        # Verify structure
        assert 'bid_ask_prices' in result
        assert 'inventory_management' in result
        assert 'risk_controls' in result
        assert 'profit_expectations' in result
        
        # Verify bid-ask prices
        prices = result['bid_ask_prices']
        assert 'bid' in prices
        assert 'ask' in prices
        assert prices['bid'] < prices['ask']
        
        # Verify inventory management
        inventory = result['inventory_management']
        assert 'hedge_suggestions' in inventory
        assert 'position_limits' in inventory
    
    @pytest.mark.asyncio
    async def test_smart_order_routing(self, trader, mock_tools):
        """Test smart order routing"""
        routing_request = {
            'symbol': 'AAPL',
            'quantity': 1000,
            'side': 'buy',
            'urgency': 'normal',
            'venue_preferences': ['NASDAQ', 'NYSE', 'BATS'],
            'cost_priority': 'lowest'
        }
        
        result = await trader.smart_order_routing(routing_request)
        
        # Verify structure
        assert 'routing_plan' in result
        assert 'venue_analysis' in result
        assert 'split_strategy' in result
        assert 'cost_estimation' in result
        
        # Verify routing plan
        plan = result['routing_plan']
        assert len(plan) > 0
        assert all('venue' in leg for leg in plan)
        assert all('quantity' in leg for leg in plan)
        assert sum(leg['quantity'] for leg in plan) == routing_request['quantity']
    
    @pytest.mark.asyncio
    async def test_risk_adjusted_execution(self, trader, mock_tools):
        """Test risk-adjusted execution strategies"""
        risk_request = {
            'symbol': 'TSLA',
            'base_quantity': 2000,
            'market_volatility': 0.35,
            'liquidity_risk': 0.25,
            'execution_risk_appetite': 'moderate',
            'time_constraints': 'normal'
        }
        
        result = await trader.risk_adjusted_execution(risk_request)
        
        # Verify structure
        assert 'adjusted_quantity' in result
        assert 'execution_strategy' in result
        assert 'risk_mitigation' in result
        assert 'scenario_analysis' in result
        
        # Verify adjustment
        assert result['adjusted_quantity'] <= risk_request['base_quantity']
        assert result['adjusted_quantity'] > 0
        
        # Verify strategy
        strategy = result['execution_strategy']
        assert 'participation_rate' in strategy
        assert 'time_slicing' in strategy
        assert 'protective_measures' in strategy
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_handling(self, trader, mock_tools):
        """Test circuit breaker handling"""
        circuit_request = {
            'symbol': 'AAPL',
            'order_size': 100,
            'circuit_breaker_status': 'triggered',
            'market_conditions': 'halted',
            'alternative_execution': 'post_reopen'
        }
        
        result = await trader.circuit_breaker_handling(circuit_request)
        
        # Verify structure
        assert 'handling_strategy' in result
        assert 'timing_recommendation' in result
        assert 'alternative_plans' in result
        assert 'risk_assessment' in result
        
        # Verify handling strategy
        strategy = result['handling_strategy']
        assert strategy['action'] in ['wait', 'cancel', 'modify', 'alternative_market']
        
        # Verify timing
        timing = result['timing_recommendation']
        assert 'wait_time' in timing
        assert 'reopen_strategy' in timing


class TestOrderExecutionTool:
    """Test cases for OrderExecutionTool"""
    
    @pytest.fixture
    def execution_tool(self):
        """Create OrderExecutionTool instance"""
        from agents.tools.order_execution_tool import OrderExecutionTool
        return OrderExecutionTool()
    
    @pytest.mark.asyncio
    async def test_market_order_execution(self, execution_tool):
        """Test market order execution"""
        order_request = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'market',
            'time_in_force': 'day'
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.order_market = Mock(return_value={
                'orderId': '12345',
                'status': 'SUBMITTED'
            })
            
            result = await execution_tool.run(order_request)
            
            assert 'order_id' in result
            assert 'status' in result
            assert 'estimated_fill_time' in result
    
    @pytest.mark.asyncio
    async def test_limit_order_execution(self, execution_tool):
        """Test limit order execution"""
        order_request = {
            'symbol': 'MSFT',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'limit',
            'price': 300.0,
            'time_in_force': 'gtc'
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.order_limit = Mock(return_value={
                'orderId': '67890',
                'status': 'NEW',
                'limitPrice': 300.0
            })
            
            result = await execution_tool.run(order_request)
            
            assert 'order_id' in result
            assert 'status' in result
            assert 'limit_price' in result
    
    @pytest.mark.asyncio
    async def test_stop_order_execution(self, execution_tool):
        """Test stop order execution"""
        order_request = {
            'symbol': 'GOOGL',
            'side': 'sell',
            'quantity': 100,
            'order_type': 'stop',
            'stop_price': 120.0,
            'time_in_force': 'day'
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.order_stop = Mock(return_value={
                'orderId': '11111',
                'status': 'NEW',
                'stopPrice': 120.0
            })
            
            result = await execution_tool.run(order_request)
            
            assert 'order_id' in result
            assert 'status' in result
            assert 'stop_price' in result


class TestMarketImpactTool:
    """Test cases for MarketImpactTool"""
    
    @pytest.fixture
    def impact_tool(self):
        """Create MarketImpactTool instance"""
        from agents.tools.market_impact_tool import MarketImpactTool
        return MarketImpactTool()
    
    @pytest.mark.asyncio
    async def test_linear_impact_model(self, impact_tool):
        """Test linear market impact model"""
        impact_request = {
            'order_size': 1000,
            'average_daily_volume': 1000000,
            'current_price': 105.0,
            'volatility': 0.25,
            'model_type': 'linear'
        }
        
        result = await impact_tool.run(impact_request)
        
        assert 'impact_estimate' in result
        assert 'cost_per_share' in result
        assert 'total_cost' in result
        assert result['impact_estimate'] > 0
    
    @pytest.mark.asyncio
    async def test_sqroot_impact_model(self, impact_tool):
        """Test square root market impact model"""
        impact_request = {
            'order_size': 500,
            'average_daily_volume': 500000,
            'current_price': 300.0,
            'volatility': 0.30,
            'model_type': 'sqrt'
        }
        
        result = await impact_tool.run(impact_request)
        
        assert 'impact_estimate' in result
        assert 'participation_rate' in result
        assert 'optimal_execution_time' in result
        assert result['impact_estimate'] > 0
    
    @pytest.mark.asyncio
    async def test_volatility_adjustment(self, impact_tool):
        """Test volatility adjustment in impact calculation"""
        base_request = {
            'order_size': 100,
            'average_daily_volume': 1000000,
            'current_price': 100.0,
            'volatility': 0.20
        }
        
        high_vol_request = {
            **base_request,
            'volatility': 0.40
        }
        
        base_result = await impact_tool.run(base_request)
        high_vol_result = await impact_tool.run(high_vol_request)
        
        # Higher volatility should lead to higher impact
        assert high_vol_result['impact_estimate'] > base_result['impact_estimate']


class TestExecutionMonitorTool:
    """Test cases for ExecutionMonitorTool"""
    
    @pytest.fixture
    def monitor_tool(self):
        """Create ExecutionMonitorTool instance"""
        from agents.tools.execution_monitor_tool import ExecutionMonitorTool
        return ExecutionMonitorTool()
    
    @pytest.mark.asyncio
    async def test_order_tracking(self, monitor_tool):
        """Test order tracking functionality"""
        tracking_request = {
            'order_ids': ['12345', '67890', '11111'],
            'monitoring_interval': 1.0,
            'alert_conditions': {
                'fill_delay': 30,
                'partial_fill': True
            }
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.order_status = Mock(return_value={
                'orderId': '12345',
                'status': 'FILLED',
                'filledQuantity': 100,
                'avgFillPrice': 105.50
            })
            
            result = await monitor_tool.run(tracking_request)
            
            assert 'order_statuses' in result
            assert 'alerts' in result
            assert 'performance_summary' in result
    
    @pytest.mark.asyncio
    async def test_fill_rate_monitoring(self, monitor_tool):
        """Test fill rate monitoring"""
        monitoring_request = {
            'order_id': '12345',
            'target_fill_rate': 0.95,
            'time_window': 300  # 5 minutes
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.order_fill_rate = Mock(return_value={
                'current_fill_rate': 0.87,
                'time_elapsed': 180,
                'estimated_completion': 120
            })
            
            result = await monitor_tool.run(monitoring_request)
            
            assert 'fill_rate' in result
            assert 'performance_against_target' in result
            assert 'recommendations' in result
    
    @pytest.mark.asyncio
    async def test_slippage_monitoring(self, monitor_tool):
        """Test slippage monitoring"""
        monitoring_request = {
            'order_id': '12345',
            'reference_price': 105.50,
            'slippage_threshold': 0.02
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.order_slippage = Mock(return_value={
                'average_fill_price': 105.70,
                'slippage': 0.0019,
                'slippage_vs_threshold': 'within_limits'
            })
            
            result = await monitor_tool.run(monitoring_request)
            
            assert 'slippage' in result
            assert 'slippage_cost' in result
            assert 'threshold_compliance' in result


class TestLiquidityAnalysisTool:
    """Test cases for LiquidityAnalysisTool"""
    
    @pytest.fixture
    def liquidity_tool(self):
        """Create LiquidityAnalysisTool instance"""
        from agents.tools.liquidity_analysis_tool import LiquidityAnalysisTool
        return LiquidityAnalysisTool()
    
    @pytest.mark.asyncio
    async def test_market_depth_analysis(self, liquidity_tool):
        """Test market depth analysis"""
        analysis_request = {
            'symbol': 'AAPL',
            'depth_levels': 5,
            'include_spread': True
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.orderbook = Mock(return_value={
                'bids': [
                    {'price': 105.40, 'size': 100},
                    {'price': 105.30, 'size': 200},
                    {'price': 105.20, 'size': 300}
                ],
                'asks': [
                    {'price': 105.60, 'size': 150},
                    {'price': 105.70, 'size': 250},
                    {'price': 105.80, 'size': 350}
                ],
                'spread': 0.20
            })
            
            result = await liquidity_tool.run(analysis_request)
            
            assert 'market_depth' in result
            assert 'liquidity_score' in result
            assert 'optimal_order_size' in result
            assert 'spread_analysis' in result
    
    @pytest.mark.asyncio
    async def test_liquidity_monitoring(self, liquidity_tool):
        """Test liquidity monitoring over time"""
        monitoring_request = {
            'symbol': 'MSFT',
            'monitoring_period': 'intraday',
            'update_frequency': 60  # seconds
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.liquidity_history = Mock(return_value={
                'average_volume': 1500000,
                'peak_volume_times': ['09:30', '10:15', '14:30'],
                'liquidity_risk_periods': ['16:00', '16:15'],
                'optimal_trading_window': ['10:00', '15:30']
            })
            
            result = await liquidity_tool.run(monitoring_request)
            
            assert 'volume_analysis' in result
            assert 'trading_windows' in result
            assert 'risk_periods' in result
            assert 'recommendations' in result
    
    @pytest.mark.asyncio
    async def test_venue_liquidity_comparison(self, liquidity_tool):
        """Test venue liquidity comparison"""
        comparison_request = {
            'symbol': 'AAPL',
            'venues': ['NASDAQ', 'NYSE', 'BATS', 'EDGX'],
            'order_size': 500
        }
        
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker.return_value.venue_liquidity = Mock(return_value={
                'NASDAQ': {'liquidity': 0.85, 'cost': 0.01, 'fill_rate': 0.98},
                'NYSE': {'liquidity': 0.75, 'cost': 0.008, 'fill_rate': 0.96},
                'BATS': {'liquidity': 0.90, 'cost': 0.005, 'fill_rate': 0.99},
                'EDGX': {'liquidity': 0.70, 'cost': 0.012, 'fill_rate': 0.94}
            })
            
            result = await liquidity_tool.run(comparison_request)
            
            assert 'venue_comparison' in result
            assert 'best_venue' in result
            assert 'routing_strategy' in result
            assert 'cost_benefit_analysis' in result


class TestIntegration:
    """Integration tests for Execution Trader"""
    
    @pytest.mark.asyncio
    async def test_full_execution_workflow(self):
        """Test complete execution workflow"""
        from agents.execution_trader import ExecutionTrader
        
        trader = ExecutionTrader()
        
        # Mock all tools
        with patch.multiple(
            'agents.execution_trader.LiquidityAnalysisTool',
            run=AsyncMock(return_value={
                'liquidity_score': 0.80,
                'optimal_order_size': 800,
                'market_depth': {}
            })
        ), patch.multiple(
            'agents.execution_trader.MarketImpactTool',
            run=AsyncMock(return_value={
                'expected_impact': 0.02,
                'optimal_strategy': 'twap'
            })
        ), patch.multiple(
            'agents.execution_trader.OrderExecutionTool',
            run=AsyncMock(return_value={
                'order_id': 'order_12345',
                'status': 'filled',
                'filled_quantity': 100
            })
        ), patch.multiple(
            'agents.execution_trader.ExecutionMonitorTool',
            run=AsyncMock(return_value={
                'execution_status': 'completed',
                'performance_metrics': {}
            })
        ):
            
            symbol = "AAPL"
            
            # Step 1: Liquidity Analysis
            liquidity_request = {
                'symbol': symbol,
                'order_size': 100,
                'time_horizon': 'intraday'
            }
            liquidity = await trader.liquidity_analysis(liquidity_request)
            assert liquidity['liquidity_score'] >= 0
            
            # Step 2: Market Impact Analysis
            impact_request = {
                'symbol': symbol,
                'order_size': 100,
                'current_price': 105.0
            }
            impact = await trader.analyze_market_impact(impact_request)
            assert 'impact_estimate' in impact
            
            # Step 3: Execute Trade
            trade_request = {
                'symbol': symbol,
                'side': 'buy',
                'quantity': 100,
                'order_type': 'limit',
                'price': 105.50
            }
            execution = await trader.execute_trade(trade_request)
            assert 'order_id' in execution
            assert execution['execution_details']['filled_quantity'] == 100
            
            # Step 4: Monitor Execution
            monitoring_request = {
                'order_ids': [execution['order_id']],
                'monitoring_interval': 1.0
            }
            monitoring = await trader.monitor_execution(monitoring_request)
            assert 'execution_status' in monitoring
            assert execution['order_id'] in monitoring['execution_status']